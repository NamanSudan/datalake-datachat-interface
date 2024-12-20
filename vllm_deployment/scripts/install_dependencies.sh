#!/bin/bash

# Exit on error
set -e

echo "Installing system dependencies..."

# Update system
dnf update -y

# Install development tools
dnf groupinstall -y "Development Tools"

# Install Python and other dependencies
dnf install -y \
    python3.11 \
    python3.11-devel \
    python3.11-pip \
    git \
    cmake \
    wget \
    gcc-c++

# Upgrade pip and install Python packages
python3.11 -m pip install --no-cache-dir -U pip setuptools wheel

# Install vLLM dependencies
python3.11 -m pip install --no-cache-dir -r requirements.txt

echo "Dependencies installed successfully" 