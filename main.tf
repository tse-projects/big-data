terraform {
  required_providers {
    aws          = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "2.17.1"
    }
  }

  required_version = ">= 0.14.9"
}

provider "digitalocean" {
  # Configuration options
  token = var.digitalocean_token
}

variable "digitalocean_token" {
  type        = string
  description = "Digitalocean Key"
}

variable "aws_access_key_id" {
  type        = string
  description = "AWS Access Key"
}

variable "aws_secret_access_key" {
  type        = string
  description = "AWS Secret Key"
}

variable "aws_session_token" {
  type        = string
  description = "AWS Secret Key"
}

variable "jwt_secret_key" {
  type        = string
  description = "JWT Secret Key"
}

variable "mongo_credentials" {
  type = object({
    MONGO_USERNAME= string
    MONGO_CLUSTER= string
    MONGO_DATABASE= string
    MONGO_PASSWORD= string
  })
  sensitive = true
}


provider "aws" {
  profile = "default"
  region  = "us-east-1"
}

resource "aws_security_group" "ssh-sg" {
  name = "ssh-sg"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "mongo-atlas-sg" {
  name = "mongo-atlas-sg"
  egress {
    from_port   = 0
    to_port     = 27017
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}


resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "generated_key" {
  key_name   = "aws_ssh_key"
  public_key = tls_private_key.ssh_key.public_key_openssh
}

resource "aws_instance" "jupyter_server" {
  ami                    = "ami-08e4e35cccc6189f4"
  instance_type          = "t2.micro"
  tags                   = {
    Name = "jupyter"
  }
  vpc_security_group_ids = [aws_security_group.ssh-sg.id]
  key_name               = aws_key_pair.generated_key.key_name
}

resource "aws_instance" "gargantua_server" {
  ami                    = "ami-08e4e35cccc6189f4"
  instance_type          = "t2.micro"
  tags                   = {
    Name = "gargantua"
  }
  vpc_security_group_ids = [aws_security_group.ssh-sg.id, aws_security_group.mongo-atlas-sg.id]
  key_name               = aws_key_pair.generated_key.key_name
}

resource "digitalocean_app" "deepbnb" {
  spec {
    name   = "deepbnb"
    region = "ams"

    # Builds a static site in the project's root directory
    # and serves it at https://foo.example.com/
    service {
      name          = "web"
      build_command = "npm run build"
      run_command   = "npm run start"

      github {
        branch         = "master"
        repo = "tse-projects/deepbnb"
        deploy_on_push = true
      }

      http_port = 3000

      routes {
        path = "/"
      }

      env {
        key   = "MONGO_USERNAME"
        value = var.mongo_credentials.MONGO_USERNAME
      }
      env {
        key   = "MONGO_CLUSTER"
        value = var.mongo_credentials.MONGO_CLUSTER
      }
      env {
        key   = "MONGO_DATABASE"
        value = var.mongo_credentials.MONGO_DATABASE
      }
      env {
        key   = "MONGO_PASSWORD"
        value = var.mongo_credentials.MONGO_PASSWORD
      }
      env {
        key   = JWT_SECRET_KEY
        value = var.jwt_secret_key
      }
      env {
        key   = "AWS_ACCESS_KEY_ID"
        value = var.aws_access_key_id
      }
      env {
        key   = "AWS_SECRET_ACCESS_KEY"
        value = var.aws_secret_access_key
      }
      env {
        key   = "AWS_SESSION_TOKEN"
        value = var.aws_session_token
      }
    }
  }
}

output "deepbnb" {
  description = "Deepbnb app"
  value       = digitalocean_app.deepbnb.live_url
}

output "jupyter" {
  description = "Jupyter server dns"
  value       = aws_instance.jupyter_server.public_dns
}

output "gargantua" {
  description = "Gargantua server dns"
  value       = aws_instance.gargantua_server.public_dns
}

output "ssh_key" {
  value = aws_key_pair.generated_key
}

resource "local_file" "ssh_key" {
  filename = "${aws_key_pair.generated_key.key_name}.pem"
  content  = tls_private_key.ssh_key.private_key_pem
}
