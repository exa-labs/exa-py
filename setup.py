from setuptools import setup, find_packages

setup(
    name="exa_py",
    version="1.1.7",
    description="Python SDK for Exa API.",
    long_description_content_type="text/markdown",
    long_description=open("README.md").read(),
    author="Exa",
    author_email="hello@exa.ai",
    package_data={"exa_py": ["py.typed"]},
    url="https://github.com/exa-labs/exa-py",
    packages=find_packages(),
    install_requires=[
        "requests",
        "typing-extensions",
        "openai>=1.10.0"
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Typing :: Typed",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
