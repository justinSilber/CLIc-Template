terraform {
  required_providers {
    linode = {
      source = "linode/linode"
      version = "1.16.0"
    }

    acme = {
      source = "vancluever/acme"
      version = "~> 2.0"
    }

    cloudflare = {
    source = "cloudflare/cloudflare"
    version = "~> 2.0"
    }
  }
}

provider "linode" {
	token = var.token
}

resource "linode_instance" "clic" {
        image = "linode/ubuntu20.04"
        label = "clic-server"
        group = "clic"
        region = "us-west"
        type = "g6-nanode-1"
        authorized_keys = var.auth_keys_tf
        root_pass = var.root_pass
  
  # This is to ensure SSH comes up before we run the local exec.
  provisioner "remote-exec" {
    inline = ["echo 'SSH connected'"]

    connection {
      type        = "ssh"
      host        = linode_instance.clic.ip_address
      user        = try("root", "clicadmin")
      private_key = file("~/.ssh/id_rsa")
    }
  }

# Add the public key from the new Linode to known_hosts so that Ansible doesn't choke on it
  provisioner "local-exec" {
    command = "ssh-keyscan -H ${linode_instance.clic.ip_address} >> ~/.ssh/known_hosts"  
  }
  
}

provider "acme" {
  server_url = "https://acme-v02.api.letsencrypt.org/directory" # <-- Production URL (Full certs, rate limited)
#  server_url = "https://acme-staging-v02.api.letsencrypt.org/directory"  # <-- Staging URL (for testing)
}

resource "tls_private_key" "private_key" {
  algorithm = "RSA"
}

resource "acme_registration" "reg" {
  account_key_pem = "${tls_private_key.private_key.private_key_pem}"
  email_address   = var.acme_registration_email
}

resource "acme_certificate" "cert" {
  account_key_pem           = "${acme_registration.reg.account_key_pem}"
  common_name               = var.common_name
#  subject_alternative_names = var.san

  dns_challenge {
    provider = "cloudflare"
    config = {
      CLOUDFLARE_DNS_API_TOKEN = var.cloudflare_token
    }
  }
}

output "linode_ip" {
    value = linode_instance.clic.ip_address
}
output "cert_private_key_pem" {
    value = acme_certificate.cert.private_key_pem
    sensitive = true
}
output "cert_certificate_pem" {
    value = acme_certificate.cert.certificate_pem
}
output "cert_intermediates" {
    value = acme_certificate.cert.issuer_pem
}
output "cert_full_chain" {
    value = join("\n", ["${acme_certificate.cert.certificate_pem}", "${acme_certificate.cert.issuer_pem}"])
}
output "cert_url" {
    value = acme_certificate.cert.certificate_url
}
