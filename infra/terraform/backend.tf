terraform {
  backend "gcs" {
    bucket = "prana-elex-staging-2816-tfstate"
    prefix = "terraform/staging"
  }
}
