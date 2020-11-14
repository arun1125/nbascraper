import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Arun", # Replace with your own username
    version="0.0.1",
    author="Arunachalam Thirunavukkarasu",
    author_email="arunthiru77@gmail.com",
    description="A Bulk NBA scraper to collect data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/arun1125/nbascraper",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)