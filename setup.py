from setuptools import find_packages, setup


setup(
    name="async-guard-toy",
    version="0.2.0",
    description="Compact benchmark for testing whether simple monitors can catch suspicious coding-agent behaviour on safe toy software tasks.",
    author="Rehan Zuberi",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=[
        "numpy>=1.17",
        "matplotlib>=3.1",
        "scikit-learn>=0.24",
    ],
)
