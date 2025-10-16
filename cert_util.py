import os
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta

def gerar_certificado(cert_path="certs/cert.pem", key_path="certs/key.pem"):
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print("🔐 Certificados SSL já existem.")
        return

    print("⚙️  Gerando certificados SSL autoassinados...")

    os.makedirs(os.path.dirname(cert_path), exist_ok=True)

    # Gera chave privada
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Gera certificado
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"BR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"São Paulo"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Carapicuíba"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"MeuApp"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(u"localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )

    # Salva os arquivos
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    print(f"✅ Certificados gerados em: {cert_path} e {key_path}")