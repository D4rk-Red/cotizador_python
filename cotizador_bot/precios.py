from config import PRECIOS_HABITACIONES
import re

def obtener_precios_habitaciones():
    """
    Retorna los precios de habitaciones desde configuración
    Puede extenderse para obtener de BD, Google Docs o API externa
    """
    return PRECIOS_HABITACIONES.copy()

def normalizar_tipo_habitacion(tipo_str):
    """
    Normaliza el nombre del tipo de habitación a formato estándar
    
    Args:
        tipo_str: String con el tipo (ej: "single", "estandar", "superior", "doble")
    
    Returns:
        String normalizado (ej: "Habitación Single")
    """
    if not tipo_str:
        return 'Habitación Estándar'  # Default
    
    tipo_lower = tipo_str.lower().strip()
    
    # Normalizar caracteres especiales
    tipo_lower = (tipo_lower
        .replace('á', 'a')
        .replace('é', 'e')
        .replace('í', 'i')
        .replace('ó', 'o')
        .replace('ú', 'u'))
    
    # Mapeo de tipos
    if 'single' in tipo_lower or 'sencilla' in tipo_lower or 'individual' in tipo_lower:
        return 'Habitación Single'
    elif 'estandar' in tipo_lower or 'standard' in tipo_lower:
        return 'Habitación Estándar'
    elif 'superior' in tipo_lower or 'premium' in tipo_lower:
        return 'Habitación Superior'
    elif 'doble' in tipo_lower or 'matrimonial' in tipo_lower or '2 camas' in tipo_lower:
        return 'Habitación Doble 2 Camas'
    else:
        return 'Habitación Estándar'  # Default

def parsear_tipos_habitaciones(tipo_habitaciones_str):
    """
    Parsea el string de tipos de habitaciones y extrae cantidades
    
    Args:
        tipo_habitaciones_str: String como "2 estandar, 1 superior" o "estandar y doble"
    
    Returns:
        Lista de tuplas: [(tipo, cantidad), ...]
        Ejemplo: [("estandar", 2), ("superior", 1)]
    """
    if not tipo_habitaciones_str:
        return []
    
    habitaciones = []
    tipo_str_lower = tipo_habitaciones_str.lower().strip()
    
    # Normalizar caracteres
    tipo_str_lower = (tipo_str_lower
        .replace('á', 'a')
        .replace('é', 'e')
        .replace('í', 'i')
        .replace('ó', 'o')
        .replace('ú', 'u'))
    
    # Separar por comas, "y", "e"
    partes = re.split(r'[,;]|\s+y\s+|\s+e\s+', tipo_str_lower)
    
    # Palabras a números
    palabras_a_numeros = {
        'un': 1, 'una': 1,
        'dos': 2,
        'tres': 3,
        'cuatro': 4,
        'cinco': 5,
        'seis': 6,
        'siete': 7,
        'ocho': 8,
        'nueve': 9,
        'diez': 10
    }
    
    # Procesar cada parte
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        
        # Patrón: "2 estandar" o "dos estandar"
        match_numero = re.search(r'^(\d+)\s*(single|estandar|standard|superior|doble|sencilla|individual|matrimonial)', parte)
        match_palabra = re.search(r'^(un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s*(single|estandar|standard|superior|doble|sencilla|individual|matrimonial)', parte)
        
        if match_numero:
            cantidad = int(match_numero.group(1))
            tipo = match_numero.group(2)
            habitaciones.append((tipo, cantidad))
        
        elif match_palabra:
            cantidad = palabras_a_numeros.get(match_palabra.group(1), 1)
            tipo = match_palabra.group(2)
            habitaciones.append((tipo, cantidad))
        
        else:
            # Solo tipo sin cantidad explícita
            if 'single' in parte or 'sencilla' in parte or 'individual' in parte:
                habitaciones.append(('single', 1))
            elif 'estandar' in parte or 'standard' in parte:
                habitaciones.append(('estandar', 1))
            elif 'superior' in parte or 'premium' in parte:
                habitaciones.append(('superior', 1))
            elif 'doble' in parte or 'matrimonial' in parte:
                habitaciones.append(('doble', 1))
    
    # Si no se encontró nada, retornar una habitación estándar
    if not habitaciones:
        habitaciones.append(('estandar', 1))
    
    return habitaciones

def calcular_totales(tipo_habitaciones_str, cantidad_noches, precios):
    """
    Calcula los totales de la cotización basado en tipos de habitaciones y noches
    
    Args:
        tipo_habitaciones_str: String con tipos y cantidades (ej: "2 estandar, 1 superior")
        cantidad_noches: Número de noches
        precios: Diccionario con precios por tipo de habitación
    
    Returns:
        Diccionario con:
        {
            "habitaciones": [
                {
                    "tipo": "Habitación Estándar",
                    "cantidad": 2,
                    "precio_noche": 50000,
                    "total": 200000
                },
                ...
            ],
            "total_neto": 300000,
            "iva": 57000,
            "total_bruto": 357000
        }
    """
    
    # Parsear tipos y cantidades
    habitaciones_parseadas = parsear_tipos_habitaciones(tipo_habitaciones_str)
    
    if not habitaciones_parseadas:
        # Fallback: 1 habitación estándar
        habitaciones_parseadas = [('estandar', 1)]
    
    habitaciones_detalle = []
    total_neto = 0
    
    # Procesar cada tipo de habitación
    for tipo, cantidad in habitaciones_parseadas:
        # Normalizar tipo
        tipo_normalizado = normalizar_tipo_habitacion(tipo)
        
        # Obtener precio
        precio_noche = precios.get(tipo_normalizado, 50000)  # Default 50k si no existe
        
        # Calcular total: cantidad de habitaciones * noches * precio por noche
        total_tipo = cantidad * cantidad_noches * precio_noche
        
        habitaciones_detalle.append({
            "tipo": tipo_normalizado,
            "cantidad": cantidad,
            "precio_noche": precio_noche,
            "total": total_tipo
        })
        
        total_neto += total_tipo
    
    # Calcular IVA (19% en Chile)
    iva = int(total_neto * 0.19)
    total_bruto = total_neto + iva
    
    return {
        "habitaciones": habitaciones_detalle,
        "total_neto": total_neto,
        "iva": iva,
        "total_bruto": total_bruto
    }

def formatear_precio(precio):
    """
    Formatea precio con separador de miles chileno
    
    Args:
        precio: Número entero
    
    Returns:
        String formateado (ej: "$50.000")
    """
    return f"${precio:,.0f}".replace(",", ".")

def validar_precios():
    """
    Valida que los precios estén configurados correctamente
    
    Returns:
        True si todo está bien, False si hay problemas
    """
    precios = obtener_precios_habitaciones()
    
    tipos_requeridos = [
        'Habitación Single',
        'Habitación Estándar',
        'Habitación Superior',
        'Habitación Doble 2 Camas'
    ]
    
    for tipo in tipos_requeridos:
        if tipo not in precios:
            print(f"⚠️ Falta configurar precio para: {tipo}")
            return False
        
        if not isinstance(precios[tipo], (int, float)) or precios[tipo] <= 0:
            print(f"⚠️ Precio inválido para {tipo}: {precios[tipo]}")
            return False
    
    return True

def obtener_precio_base():
    """
    Retorna el precio base más bajo para referencia
    
    Returns:
        Precio entero
    """
    precios = obtener_precios_habitaciones()
    return min(precios.values())

def obtener_precio_maximo():
    """
    Retorna el precio más alto para referencia
    
    Returns:
        Precio entero
    """
    precios = obtener_precios_habitaciones()
    return max(precios.values())

def calcular_descuento(total_neto, cantidad_noches):
    """
    Calcula descuentos por cantidad de noches (opcional)
    
    Args:
        total_neto: Total neto sin descuentos
        cantidad_noches: Número de noches
    
    Returns:
        Diccionario con descuento aplicado:
        {
            "descuento_porcentaje": 10,
            "descuento_monto": 30000,
            "total_con_descuento": 270000
        }
    """
    descuento_porcentaje = 0
    
    # Descuentos por estadía larga
    if cantidad_noches >= 7:
        descuento_porcentaje = 15  # 15% para 7+ noches
    elif cantidad_noches >= 5:
        descuento_porcentaje = 10  # 10% para 5-6 noches
    elif cantidad_noches >= 3:
        descuento_porcentaje = 5   # 5% para 3-4 noches
    
    descuento_monto = int(total_neto * (descuento_porcentaje / 100))
    total_con_descuento = total_neto - descuento_monto
    
    return {
        "descuento_porcentaje": descuento_porcentaje,
        "descuento_monto": descuento_monto,
        "total_con_descuento": total_con_descuento
    }

def generar_resumen_precios():
    """
    Genera un resumen de todos los precios disponibles
    
    Returns:
        String formateado con todos los precios
    """
    precios = obtener_precios_habitaciones()
    
    resumen = "📋 *LISTA DE PRECIOS*\n\n"
    
    for tipo, precio in sorted(precios.items()):
        resumen += f"• {tipo}: {formatear_precio(precio)} por noche\n"
    
    resumen += f"\n💡 Precio desde: {formatear_precio(obtener_precio_base())}"
    
    return resumen

# Función de testing
if __name__ == "__main__":
    print("🧪 Testing módulo de precios...\n")
    
    # Test 1: Validar precios
    print("Test 1: Validar precios")
    if validar_precios():
        print("✅ Precios válidos\n")
    else:
        print("❌ Error en precios\n")
    
    # Test 2: Parsear tipos
    print("Test 2: Parsear tipos de habitaciones")
    casos = [
        "2 estandar, 1 superior",
        "estandar y doble",
        "una superior",
        "3 dobles",
        "single"
    ]
    
    for caso in casos:
        resultado = parsear_tipos_habitaciones(caso)
        print(f"  '{caso}' -> {resultado}")
    print()
    
    # Test 3: Calcular totales
    print("Test 3: Calcular totales")
    precios = obtener_precios_habitaciones()
    resultado = calcular_totales("2 estandar, 1 superior", 3, precios)
    
    print(f"  Habitaciones: {resultado['habitaciones']}")
    print(f"  Total Neto: {formatear_precio(resultado['total_neto'])}")
    print(f"  IVA: {formatear_precio(resultado['iva'])}")
    print(f"  Total Bruto: {formatear_precio(resultado['total_bruto'])}")
    print()
    
    # Test 4: Generar resumen
    print("Test 4: Resumen de precios")
    print(generar_resumen_precios())