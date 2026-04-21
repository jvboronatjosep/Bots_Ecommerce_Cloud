#!/usr/bin/env python3
"""Script de prueba para verificar la integración con Cloud SQL"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bots/woocommerce_bot"))

from data.database import CloudSQLConnection, AddressRepository, format_address_from_db
from data.fake_customer import CustomerGenerator

def test_connection():
    print("=" * 60)
    print("🔍 PROBANDO CONEXIÓN A CLOUD SQL")
    print("=" * 60)

    db = CloudSQLConnection()
    if db.test_connection():
        print("✅ Conexión a Cloud SQL: OK")
        return db
    else:
        print("❌ Error: No se pudo conectar a Cloud SQL")
        return None


def test_repository(db):
    print("\n" + "=" * 60)
    print("🔍 PROBANDO REPOSITORIO DE DIRECCIONES")
    print("=" * 60)

    repo = AddressRepository(db)

    stats = repo.get_province_stats()
    print(f"\n📊 Estadísticas de provincias:")
    print(f"   Total de provincias: {len(stats)}")
    for prov, count in sorted(stats.items())[:5]:
        print(f"   - {prov}: {count} direcciones")

    addr = repo.get_random_address()
    if addr:
        print(f"\n📍 Dirección aleatoria obtenida:")
        print(f"   Vía: {addr.get('nombre_via')}")
        print(f"   Número: {addr.get('numero')}")
        print(f"   CP: {addr.get('cod_postal')}")
        print(f"   Municipio: {addr.get('municipio')}")
        print(f"   Provincia: {addr.get('provincia')}")

    return repo


def test_customer_generation():
    print("\n" + "=" * 60)
    print("🔍 PROBANDO GENERACIÓN DE CLIENTES")
    print("=" * 60)

    gen = CustomerGenerator(province=None)
    print("\n👤 Cliente sin provincia especificada:")
    customer = gen.generate()
    print(f"   Nombre: {customer.first_name} {customer.last_name}")
    print(f"   Email: {customer.email}")
    print(f"   Dirección: {customer.address1}")
    print(f"   CP: {customer.zip_code}")
    print(f"   Ciudad: {customer.city}")
    print(f"   Provincia: {customer.province_code}")
    print(f"   País: {customer.country_code}")
    print(f"   Fuente: {customer.fuente}")

    print("\n👤 Cliente con provincia 'Madrid':")
    gen_madrid = CustomerGenerator(province="Madrid")
    customer_madrid = gen_madrid.generate()
    print(f"   Nombre: {customer_madrid.first_name} {customer_madrid.last_name}")
    print(f"   Dirección: {customer_madrid.address1}")
    print(f"   CP: {customer_madrid.zip_code}")
    print(f"   Provincia: {customer_madrid.province_code}")
    print(f"   Fuente: {customer_madrid.fuente}")

    print("\n👤 Cliente con provincia 'Barcelona':")
    gen_barcelona = CustomerGenerator(province="B")
    customer_barcelona = gen_barcelona.generate()
    print(f"   Nombre: {customer_barcelona.first_name} {customer_barcelona.last_name}")
    print(f"   Dirección: {customer_barcelona.address1}")
    print(f"   CP: {customer_barcelona.zip_code}")
    print(f"   Provincia: {customer_barcelona.province_code}")
    print(f"   Fuente: {customer_barcelona.fuente}")


def main():
    print("\n🚀 PRUEBA DE INTEGRACIÓN CLOUD SQL → WooCommerce Bot\n")

    db = test_connection()
    if not db:
        print("\n❌ No se puede continuar sin conexión a BD")
        return False

    repo = test_repository(db)
    if not repo:
        print("\n❌ Error al probar repositorio")
        return False

    try:
        test_customer_generation()
        print("\n" + "=" * 60)
        print("✅ TODAS LAS PRUEBAS PASARON")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"\n❌ Error durante prueba de clientes: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
