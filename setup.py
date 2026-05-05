"""Setup configuration for WireFall package."""
from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='wirefall',
    version='0.2.0',
    author='anotherboohoohoo',
    description='WireFall — Network Firewall & Connection Monitor',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/anotherboohoohoo/Big-Bag-O-AI',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Networking',
        'Topic :: Security',
    ],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'wirefall=src.main:main',
        ],
    },
)
