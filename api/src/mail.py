def send_mock_verification_mail(mail: str, token: str):
    print(f"""
    Mock e-mail to {mail}
    Verification link: http://localhost:8000/verify-account/{token}
    """)
