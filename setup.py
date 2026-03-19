from setuptools import find_packages, setup


setup(
    name="async-guard-toy",
    version="0.1.0",
    description="Toy environments and baseline monitors for asynchronous monitoring of LLM coding-agent actions.",
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
