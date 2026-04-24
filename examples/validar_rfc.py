"""
Validador de RFC Mexicano con tests unittest.
Version funcional sin bugs.
"""
import re
import unittest


def valida_rfc(rfc):
    """Valida formato basico de RFC mexicano (fisica y moral)."""
    if not isinstance(rfc, str):
        return False
    
    rfc = rfc.upper().strip()
    
    # Persona fisica: 4 letras + 6 digitos + 3 alfanumericos
    patron_fisica = r'^[A-ZÑ&]{4}[0-9]{6}[A-Z0-9]{3}$'
    # Persona moral: 3 letras + 6 digitos + 3 alfanumericos
    patron_moral = r'^[A-ZÑ&]{3}[0-9]{6}[A-Z0-9]{3}$'
    
    if not (re.match(patron_fisica, rfc) or re.match(patron_moral, rfc)):
        return False
    
    # Validar fecha
    try:
        if re.match(patron_fisica, rfc):
            fecha_str = rfc[4:10]
        else:
            fecha_str = rfc[3:9]
        
        ano = int(fecha_str[0:2])
        mes = int(fecha_str[2:4])
        dia = int(fecha_str[4:6])
        
        if not (1 <= mes <= 12):
            return False
        if not (1 <= dia <= 31):
            return False
    except ValueError:
        return False
    
    return True


class TestValidaRFC(unittest.TestCase):
    
    def test_rfc_fisica_valido(self):
        self.assertTrue(valida_rfc("VECJ880326XXX"))
        self.assertTrue(valida_rfc("PERJ750101ABC"))
    
    def test_rfc_moral_valido(self):
        self.assertTrue(valida_rfc("ABC010101ABC"))
        self.assertTrue(valida_rfc("XYZ990101123"))
    
    def test_longitud_invalida(self):
        self.assertFalse(valida_rfc("VECJ88"))
        self.assertFalse(valida_rfc("VECJ880326XXXX"))
    
    def test_fecha_invalida(self):
        self.assertFalse(valida_rfc("VECJ881326XXX"))  # mes 13
        self.assertFalse(valida_rfc("VECJ880132XXX"))  # dia 32
    
    def test_caracteres_invalidos(self):
        self.assertFalse(valida_rfc("1234880326XXX"))
        self.assertFalse(valida_rfc("VECJ88-326XXX"))
        self.assertTrue(valida_rfc("vecj880326xxx"))  # minusculas OK
    
    def test_tipos_invalidos(self):
        self.assertFalse(valida_rfc(None))
        self.assertFalse(valida_rfc(12345))


if __name__ == "__main__":
    unittest.main()
