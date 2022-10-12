from setuptools import setup

setup(
    name="closable_cpython_issues",
    version="1.0",
    author="Shantanu Jain",
    py_modules=["closable_cpython_issues"],
    entry_points={"console_scripts": ["closable_cpython_issues=closable_cpython_issues:main"]},
    install_requires=["requests"],
    python_requires=">=3.9",
)
