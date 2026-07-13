from app.detection.validators import inn_ok,luhn_ok

def test_known_inn_org(): assert inn_ok('7707083893')
def test_luhn(): assert luhn_ok('4111111111111111')
