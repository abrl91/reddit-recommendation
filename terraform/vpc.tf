# VPC and Networking Configuration
#
# Creates an isolated network with:
# - VPC (virtual private cloud - your private network)
# - Public subnet (instances get public IPs)
# - Internet gateway (connection to internet)
# - Route table (traffic routing rules)

# Get available AZs in the region
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC - Your isolated network
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "reddit-recommendation-vpc"
  }
}

# Internet Gateway - Allows VPC to access internet
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "reddit-recommendation-igw"
  }
}

# Public Subnet - Where our EC2 will live
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "reddit-recommendation-public-subnet"
  }
}

# Route Table - Traffic rules for the subnet
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  # Route all outbound traffic to internet gateway
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "reddit-recommendation-public-rt"
  }
}

# Associate route table with subnet
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
