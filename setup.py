import os
from setuptools import setup, find_packages

# Read requirements
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#') and not line.startswith('--')]

setup(
    name="vllm",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    author="Your Name",
    author_email="your.email@example.com",
    description="vLLM CPU implementation for ARM processors",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/vllm",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
) 