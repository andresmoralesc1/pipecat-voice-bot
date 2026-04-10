"""Test suite para text_normalizer.py - Tarea 11"""

import sys
from text_normalizer import normalize_customer_name, normalize_text, _capitalize_names, _normalize_numbers

def test_normalize_customer_name():
    """Test de normalización de nombres de clientes."""
    print("Test 1: Normalización de nombres de clientes")
    
    tests = [
        ("maría", "María"),
        ("montserrat", "Montserrat"),
        ("jordi", "Jordi"),
        ("núria", "Núria"),
        ("david", "David"),
        ("ana", "Ana"),
        ("xavier", "Xavier"),
        ("jose", "Jose"),
    ]
    
    passed = 0
    failed = 0
    
    for input_name, expected in tests:
        result = normalize_customer_name(input_name)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {input_name} → {result} (esperado: {expected})")
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"  Resultado: {passed}/{len(tests)} pasados\n")
    return failed == 0

def test_normalize_numbers():
    """Test de normalización de números."""
    print("Test 2: Normalización de números")
    
    tests = [
        ("seis uno dos", "612"),
        ("nueve ocho siete", "987"),
        ("uno dos tres", "123"),
        ("tres", "tres"),  # Un solo dígito no se cambia
        ("seis", "seis"),  # Un solo dígito no se convierte
    ]
    
    passed = 0
    failed = 0
    
    for input_num, expected in tests:
        result = normalize_text(input_num)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {input_num} → {result} (esperado: {expected})")
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"  Resultado: {passed}/{len(tests)} pasados\n")
    return failed == 0

def test_full_sentences():
    """Test de normalización en oraciones completas."""
    print("Test 3: Normalización de oraciones completas")
    
    tests = [
        ("me llamo maría", "me llamo María"),
        ("soy jordi", "soy Jordi"),
        ("mi número es seis uno dos", "mi número es 612"),
        ("reservar para montserrat", "reservar para Montserrat"),
    ]
    
    passed = 0
    failed = 0
    
    for input_text, expected in tests:
        result = normalize_text(input_text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {input_text} → {result} (esperado: {expected})")
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"  Resultado: {passed}/{len(tests)} pasados\n")
    return failed == 0

def test_edge_cases():
    """Test de casos especiales."""
    print("Test 4: Casos especiales")
    
    tests = [
        ("", ""),  # Vacío
        (None, ""),  # None
        ("MARÍA", "MARÍA"),  # Mayúsculas (no se modifica)
        ("123", "123"),  # Solo números
        ("hola mundo", "hola mundo"),  # Sin nombres/números
    ]
    
    passed = 0
    failed = 0
    
    for input_text, expected in tests:
        result = normalize_text(input_text) if input_text is not None else normalize_text(input_text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {input_text} → {result} (esperado: {expected})")
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"  Resultado: {passed}/{len(tests)} pasados\n")
    return failed == 0

def main():
    """Ejecutar todos los tests."""
    print("=" * 60)
    print("TEST SUITE - TEXT NORMALIZER (TAREA 11)")
    print("=" * 60 + "\n")
    
    results = []
    results.append(("Nombres de clientes", test_normalize_customer_name()))
    results.append(("Normalización de números", test_normalize_numbers()))
    results.append(("Oraciones completas", test_full_sentences()))
    results.append(("Casos especiales", test_edge_cases()))
    
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n✅ TODOS LOS TESTS PASARON")
        return 0
    else:
        print("\n❌ ALGUNOS TESTS FALLARON")
        return 1

if __name__ == "__main__":
    sys.exit(main())
