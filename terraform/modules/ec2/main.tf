# 1. Ask AWS: "Give me the ID for Ubuntu 22.04 in WHATEVER region I am in right now"
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical (Official Ubuntu Owner)

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# 2. Create the Server using that dynamic ID
resource "aws_instance" "ingestion_server" {
  ami           = data.aws_ami.ubuntu.id 
  instance_type = "t3.micro" # t3.micro is the standard cheap option in eu-north-1
  
  iam_instance_profile = var.iam_instance_profile
  
  tags = {
    Name = "Citibike-Ingestion-Host"
  }
}