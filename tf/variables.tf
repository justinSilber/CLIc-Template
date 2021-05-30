variable "token" {
	description = "Linode API Access Token"
    type        = string
    sensitive   = true
}

variable "root_pass" {
	description = "Root user password for this instance"
    type        = string
    sensitive   = true
}

variable "auth_keys_tf" {
	description = "Array of authorized public RSA keys"
    type        = list(string)
    sensitive   = true
}

variable "acme_registration_email" {
    description = "Email address for TLS cert"
    type        = string
}

variable "common_name" {
    description = "Domain name for target site"
    type        = string
}

# variable "san" {
#     description = "Subject Alternative Name"
#     type        = set(string)
# }

variable "cloudflare_token" {
	description = "Cloudflare API token"
    type        = string
    sensitive   = true
}

variable "cloudflare_zone_id" {
    description = "Cloudflare zone ID"
    type        = string
    sensitive   = true
}

# variable "a_name" {
#     description = "A record name"
#     type        = string
#     sensitive   = false
# }

variable "cloudflare_email" {
    description = "Email address with Cloudflare"
    type        = string
    sensitive   = true
}

# variable "cloudflare_api_key" {
#     description = "Cloudflare API key"
#     type        = string
#     sensitive   = true
# }