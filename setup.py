import os
import re

# To use a consistent encoding
from codecs import open as copen
from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the relevant file
with copen(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


def read(*parts):
    with copen(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


__version__ = find_version("omop2obo", "__version__.py")

test_deps = [
    'codacy-coverage',
    'coveralls',
    'mock',
    'mypy',
    'pytest',
    'pytest-cov',
    'validate_version_code'
]

extras = {
    'test': test_deps,
}

setup(
    name='omop2obo',
    version=__version__,
    description="OMOP2OBO is the first health system-wide, disease-agnostic mappings between standardized clinical "
                "terminologies in the Observational Medical Outcomes Partnership (OMOP) common data model and several "
                "Open Biomedical Ontologies (OBO).",
    long_description=long_description,
    url="https://github.com/callahantiff/OMOP2OBO",
    author="callahantiff@gmail.com",
    author_email="callahantiff",

    # Choose your license
    license='MIT',
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    tests_require=test_deps,

    # Add here the package dependencies
    install_requires=[
        'click==8.0.0a1',
        'lxml==4.6.3',
        'more-itertools==8.6.0',
        'nltk==3.5',
        'oauth2client==4.1.3',
        'openpyxl==3.0.5',
        'pandas==1.1.5',
        'rdflib==5.0.0',
        'regex==2020.11.13',
        'responses==0.10.12',
        'scipy==1.5.4',
        'scikit-learn==0.23.2',
        'tqdm==4.54.1',
        'types-requests'],
    extras_require=extras,
)
