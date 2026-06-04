def send_mock_verification_mail(mail: str, token: str):
    print(f"""
    Mock e-mail to {mail}
    Verification link: http://localhost:8000/verify-account/{token}
    """)

def send_mock_reset_password_mail(mail: str, token: str):
    print(f"""
    Mock e-mail to {mail}
    Reset password link: http://localhost:8000/reset-password/{token}
    """)
