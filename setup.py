from setuptools import setup, find_packages

setup(
    name='metaphor-python',
    version='0.1.10',
    description='A Python package for the Metaphor API.',
    author='Metaphor',
    author_email='hello@metaphor.systems',
    url='https://github.com/metaphorsystems/metaphor-python',
    packages=find_packages(),
    install_requires=[
        'requests',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
