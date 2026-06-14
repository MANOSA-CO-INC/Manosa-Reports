from setuptools import setup, find_packages

setup(
    name='manosa_reports',
    version='0.0.1',
    description='Custom reports for Mañosa & Co.',
    author='Mañosa & Co., Inc.',
    author_email='admin@manosa.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=['frappe'],
)
