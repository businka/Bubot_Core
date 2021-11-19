from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_pem_rsa_key(name, path=''):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    with open(f'{path}{name}_key.pem', 'wb') as file:
        file.write(private_key.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.TraditionalOpenSSL,
            crypto_serialization.NoEncryption()
        ))
    with open(f'{path}{name}_cert.pem', 'wb') as file:
        file.write(public_key.public_bytes(
            crypto_serialization.Encoding.OpenSSH,
            crypto_serialization.PublicFormat.OpenSSH
        ))
if __name__ == '__main__':
    generate_pem_rsa_key('test')