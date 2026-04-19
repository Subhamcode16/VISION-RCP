from setuptools import setup, find_packages

setup(
    name="vision-rcp",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.32.0",
        "websockets>=13.0",
        "pydantic>=2.9.0",
        "psutil>=6.1.0",
        "PyJWT>=2.9.0",
        "cryptography>=43.0.0",
        "aiosqlite>=0.20.0",
        "python-dotenv>=1.0.0",
        "slowapi>=0.1.9",
        "click>=8.1.0",
        "qrcode[pil]>=7.4",
        "Pillow>=10.0",
    ],
    entry_points={
        "console_scripts": [
            "vision-rcp=src.cli:cli",
        ],
    },
    python_requires=">=3.10",
)
