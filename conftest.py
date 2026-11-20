"""Fixtures compartidas de pytest sobre PostgreSQL."""

import pytest

from acceso.models import Rol, Usuario
from tenants.models import Almacen, Region, Tenant


@pytest.fixture
def usuario_admin(db):
    return Usuario.objects.create_user(
        email="admin@lari.local",
        password="ClaveAdmin12345",
        rol=Rol.ADMIN_PLATAFORMA,
        is_active=True,
    )


@pytest.fixture
def region(db, usuario_admin):
    return Region.objects.create(
        codigo="LIM",
        nombre="Lima",
        creado_por=usuario_admin,
    )


@pytest.fixture
def almacen(db, region, usuario_admin):
    return Almacen.objects.create(
        region=region,
        centro="PR05",
        codigo_almacen="BE03",
        buzon="almacen.lim@lari.local",
        creado_por=usuario_admin,
    )


@pytest.fixture
def tenant(db, region, usuario_admin):
    return Tenant.objects.create(
        codigo="TEN-001",
        nombre="Tenant de prueba",
        region=region,
        creado_por=usuario_admin,
    )


@pytest.fixture
def usuario_tenant(db, tenant):
    return Usuario.objects.create_user(
        email="tenant@lari.local",
        password="ClaveTenant12345",
        rol=Rol.USUARIO_TENANT,
        tenant=tenant,
        is_active=True,
    )


@pytest.fixture
def usuario_almacen(db, region):
    return Usuario.objects.create_user(
        email="almacen@lari.local",
        password="ClaveAlmacen12345",
        rol=Rol.RESPONSABLE_ALMACEN,
        region=region,
        is_active=True,
    )


@pytest.fixture
def usuario_otro_tenant(db, region, usuario_admin):
    otro = Tenant.objects.create(
        codigo="TEN-002",
        nombre="Otro tenant",
        region=region,
        creado_por=usuario_admin,
    )
    return Usuario.objects.create_user(
        email="otro@lari.local",
        password="ClaveOtro12345",
        rol=Rol.USUARIO_TENANT,
        tenant=otro,
        is_active=True,
    )


@pytest.fixture
def material(db, usuario_almacen):
    from materiales.models import Material

    return Material.objects.create(
        codigo="10402520279",
        descripcion="ROSETA",
        lote="FIBERHOME",
        es_seriado=True,
        creado_por=usuario_almacen,
    )


@pytest.fixture
def verificacion_movimientos():
    """Registra verificaciones de movimientos y las limpia al terminar."""
    from materiales import services

    bajas = []

    def registrar(func):
        bajas.append(services.registrar_verificacion_movimientos(func))

    yield registrar

    for baja in bajas:
        baja()


@pytest.fixture
def tecnico(db, tenant, usuario_tenant):
    from tecnicos.models import Tecnico

    return Tecnico.objects.create(
        tenant=tenant,
        nif="LA1234",
        nombre="Juan Pérez",
        activo=True,
        creado_por=usuario_tenant,
    )


@pytest.fixture
def tecnico_desactivado(db, tenant, usuario_tenant):
    from tecnicos.models import Tecnico

    return Tecnico.objects.create(
        tenant=tenant,
        nif="LA5678",
        nombre="Ana Desactivada",
        activo=False,
        creado_por=usuario_tenant,
    )


@pytest.fixture
def tecnico_otro_tenant(db, usuario_otro_tenant):
    from tecnicos.models import Tecnico

    return Tecnico.objects.create(
        tenant=usuario_otro_tenant.tenant,
        nif="LA9999",
        nombre="Técnico Ajeno",
        activo=True,
        creado_por=usuario_otro_tenant,
    )


@pytest.fixture
def registro_cambios():
    from auditoria.models import RegistroCambio

    def consultar(objeto, entidad=None):
        return RegistroCambio.objects.filter(
            entidad=entidad or objeto.__class__.__name__,
            entidad_id=objeto.pk,
        )

    return consultar


@pytest.fixture
def material_seriado(db, usuario_almacen):
    from materiales.models import Material

    return Material.objects.create(
        codigo="10402520323",
        descripcion="ROSETA ÓPTICA",
        lote="FIBERHOME",
        es_seriado=True,
        creado_por=usuario_almacen,
    )


@pytest.fixture
def material_no_seriado(db, usuario_almacen):
    from materiales.models import Material

    return Material.objects.create(
        codigo="10402520400",
        descripcion="CABLE UTP",
        lote="",
        es_seriado=False,
        creado_por=usuario_almacen,
    )


@pytest.fixture
def serie_existente(db, tenant, material_seriado, usuario_tenant):
    from series.models import Serie

    return Serie.objects.create(
        numero="ABC123456789",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        creado_por=usuario_tenant,
    )


@pytest.fixture
def stock_general(db, tenant, material_seriado):
    from stock.models import StockGeneral

    return StockGeneral.objects.create(
        tenant=tenant,
        material=material_seriado,
        cantidad=100,
    )


@pytest.fixture
def stock_tecnico(db, tenant, tecnico, material_seriado):
    from stock.models import StockTecnico

    return StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_seriado,
        cantidad=10,
    )


@pytest.fixture
def recojo(db, tenant, usuario_tenant, material_no_seriado):
    from datetime import date

    from recojos.models import LineaRecojo, Recojo

    rec = Recojo.objects.create(
        tenant=tenant,
        region=tenant.region,
        nombre="Recojo de prueba",
        fecha=date.today(),
        creado_por=usuario_tenant,
    )
    LineaRecojo.objects.create(
        tenant=tenant,
        recojo=rec,
        material=material_no_seriado,
        lote=material_no_seriado.lote,
        serie=None,
        cantidad=5,
    )
    return rec


@pytest.fixture
def cliente_autenticado(usuario_admin):
    from django.test import Client

    cliente = Client()
    cliente.force_login(usuario_admin)
    session = cliente.session
    session["version_sesion"] = usuario_admin.version_sesion
    session.save()
    return cliente


@pytest.fixture
def sesion_con_version(client, usuario_tenant):
    client.force_login(usuario_tenant)
    session = client.session
    session["version_sesion"] = usuario_tenant.version_sesion
    session.save()
    return client


@pytest.fixture
def cliente_tenant(sesion_con_version):
    return sesion_con_version


@pytest.fixture
def cliente_almacen(usuario_almacen):
    from django.test import Client

    cliente = Client()
    cliente.force_login(usuario_almacen)
    session = cliente.session
    session["version_sesion"] = usuario_almacen.version_sesion
    session.save()
    return cliente


@pytest.fixture
def cliente_otro_tenant(usuario_otro_tenant):
    from django.test import Client

    cliente = Client()
    cliente.force_login(usuario_otro_tenant)
    session = cliente.session
    session["version_sesion"] = usuario_otro_tenant.version_sesion
    session.save()
    return cliente
