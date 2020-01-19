"Setup script for D2TXT"

import setuptools


with open('README.md', 'r') as readme_md:
    readme = readme_md.read()

setuptools.setup(
    name='d2txt',
    version='0.0.1',
    author='Yehyoung Kang',
    author_email='keepyourhonor@gmail.com',
    description='Parses Diablo II\'s TXT files and converts them to INI files',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/pastelmind/d2txt',
    py_modules=['d2txt'],
    install_requires=[
        'qtoml >= 0.3.0, <1',
        'toml >= 0.10.0, <1',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
    ],
    python_requires='>=3.6',
)
