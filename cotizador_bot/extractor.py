import requests
import json
from datetime import datetime, timedelta
from config import OPENAI_API_KEY

def extraer_informacion_reserva(mensaje):
    """
    Extrae información de reserva usando OpenAI GPT-4
    Retorna diccionario con: check_in, check_out, cant_personas, 
    cantidad_habitaciones, tipo_habitaciones
    """
    
    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    fecha_actual_obj = datetime.now()
    
    # Calcular fechas de referencia
    manana = (fecha_actual_obj + timedelta(days=1)).strftime('%Y-%m-%d')
    pasado_manana = (fecha_actual_obj + timedelta(days=2)).strftime('%Y-%m-%d')
    
    system_prompt = f"""Hoy es {fecha_actual}. Zona horaria: America/Santiago (UTC-3)

Eres un extractor de información para reservas de hotel. Tu tarea es identificar datos para una reserva ÚNICAMENTE si el usuario los menciona. Si un dato no aparece en el mensaje del usuario, no debes inventarlo ni asumirlo.

Solo debes extraer estos datos:
- check_in: Fecha de entrada (formato YYYY-MM-DD)
- check_out: Fecha de salida (formato YYYY-MM-DD)
- cant_personas: Cantidad de personas
- cantidad_habitaciones: Cantidad de habitaciones
- tipo_habitaciones: Tipo de habitaciones (single, estandar, superior, doble)

REGLAS IMPORTANTES:

1. Si el usuario NO menciona ninguna fecha, día o referencia de tiempo, NO debes entregar día de entrada ni día de salida.

2. Si el usuario SÍ menciona una fecha o un día, entonces debes generar:
   - Día de entrada según lo que diga el usuario
   - Día de salida: normalmente es el día siguiente, a menos que el usuario dé un rango (ejemplo: del 12 al 15)

3. Referencias de tiempo comunes:
   - "mañana" = {manana}
   - "pasado mañana" = {pasado_manana}
   - "hoy" = {fecha_actual}
   - Si menciona día de semana (lunes, martes, etc.), calcular la fecha más cercana

4. Si el usuario menciona un día numérico sin mes (por ejemplo: "del 15 al 18"), y la fecha actual ya pasó esos días del mes, entonces se interpreta que se refiere al mes siguiente.

5. Si el usuario menciona cantidad de personas, extrae ese valor. Si no la menciona, NO inventes nada.

6. Si el usuario menciona cantidad de habitaciones, extráelo. Si no lo menciona, puedes asumir 1 solo si ya existe una fecha y personas. Si el usuario no menciona fechas, NO asumas habitaciones.

7. Para tipo_habitaciones, normaliza a: "single", "estandar", "superior", "doble"
   - Si menciona múltiples habitaciones, indica cantidad y tipo: "2 estandar", "1 superior y 1 doble"

RESPONDE SOLO CON UN JSON VÁLIDO (sin markdown, sin backticks, sin explicaciones):
{{"check_in": null, "check_out": null, "cant_personas": null, "cantidad_habitaciones": null, "tipo_habitaciones": null}}

Reemplaza null con los valores encontrados o mantén null si no se mencionan."""

    user_prompt = f'Mensaje del cliente: "{mensaje}"'

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            texto_respuesta = data['choices'][0]['message']['content'].strip()
            
            # Limpiar markdown si existe
            texto_respuesta = texto_respuesta.replace('```json', '').replace('```', '').strip()
            
            # Parsear JSON
            resultado = json.loads(texto_respuesta)
            
            # Procesar y validar fechas
            resultado = procesar_fechas(resultado, fecha_actual)
            
            # Validar y limpiar datos
            resultado = validar_datos(resultado)
            
            print(f"✅ Información extraída por OpenAI: {resultado}")
            return resultado
            
        else:
            print(f"⚠️ Error en API OpenAI: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return extraccion_fallback(mensaje)
            
    except json.JSONDecodeError as e:
        print(f"⚠️ Error parseando JSON de OpenAI: {e}")
        return extraccion_fallback(mensaje)
    except Exception as e:
        print(f"⚠️ Error extrayendo información: {e}")
        import traceback
        traceback.print_exc()
        return extraccion_fallback(mensaje)

def procesar_fechas(resultado, fecha_actual_str):
    """Procesa y normaliza las fechas extraídas"""
    fecha_actual = datetime.strptime(fecha_actual_str, '%Y-%m-%d')
    
    # Procesar check_in
    if resultado.get('check_in'):
        check_in_str = resultado['check_in']
        
        # Si contiene texto descriptivo, intentar convertir
        if isinstance(check_in_str, str):
            # Verificar si es una fecha válida
            try:
                check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d')
                
                # Si la fecha es anterior a hoy, intentar ajustar al mes siguiente
                if check_in_date < fecha_actual:
                    diferencia_dias = (fecha_actual - check_in_date).days
                    
                    # Si la diferencia es pequeña (menos de 60 días), probablemente es del mes siguiente
                    if diferencia_dias < 60:
                        check_in_date = check_in_date.replace(
                            month=check_in_date.month + 1 if check_in_date.month < 12 else 1,
                            year=check_in_date.year + 1 if check_in_date.month == 12 else check_in_date.year
                        )
                        resultado['check_in'] = check_in_date.strftime('%Y-%m-%d')
                
            except ValueError:
                # No es una fecha válida, dejar como null
                resultado['check_in'] = None
    
    # Procesar check_out
    if resultado.get('check_out'):
        check_out_str = resultado['check_out']
        
        if isinstance(check_out_str, str):
            try:
                check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d')
                
                # Si check_out es anterior a check_in, ajustar
                if resultado.get('check_in'):
                    check_in_date = datetime.strptime(resultado['check_in'], '%Y-%m-%d')
                    
                    if check_out_date <= check_in_date:
                        # Usar el mismo mes que check_in
                        check_out_date = check_out_date.replace(
                            year=check_in_date.year,
                            month=check_in_date.month
                        )
                        
                        # Si sigue siendo anterior, es del mes siguiente
                        if check_out_date <= check_in_date:
                            if check_out_date.month < 12:
                                check_out_date = check_out_date.replace(month=check_out_date.month + 1)
                            else:
                                check_out_date = check_out_date.replace(month=1, year=check_out_date.year + 1)
                        
                        resultado['check_out'] = check_out_date.strftime('%Y-%m-%d')
                
                # Si check_out es anterior a hoy
                elif check_out_date < fecha_actual:
                    diferencia_dias = (fecha_actual - check_out_date).days
                    
                    if diferencia_dias < 60:
                        check_out_date = check_out_date.replace(
                            month=check_out_date.month + 1 if check_out_date.month < 12 else 1,
                            year=check_out_date.year + 1 if check_out_date.month == 12 else check_out_date.year
                        )
                        resultado['check_out'] = check_out_date.strftime('%Y-%m-%d')
                
            except ValueError:
                resultado['check_out'] = None
    
    return resultado

def validar_datos(resultado):
    """Valida y limpia los datos extraídos"""
    
    # Convertir valores vacíos a None
    for key in resultado.keys():
        if resultado[key] == "" or resultado[key] == "null":
            resultado[key] = None
    
    # Validar cantidad_personas
    if resultado.get('cant_personas'):
        try:
            cant = int(resultado['cant_personas'])
            if cant <= 0 or cant > 50:  # Límite razonable
                resultado['cant_personas'] = None
            else:
                resultado['cant_personas'] = str(cant)
        except (ValueError, TypeError):
            resultado['cant_personas'] = None
    
    # Validar cantidad_habitaciones
    if resultado.get('cantidad_habitaciones'):
        try:
            cant = int(resultado['cantidad_habitaciones'])
            if cant <= 0 or cant > 20:  # Límite razonable
                resultado['cantidad_habitaciones'] = None
            else:
                resultado['cantidad_habitaciones'] = str(cant)
        except (ValueError, TypeError):
            resultado['cantidad_habitaciones'] = None
    
    # Normalizar tipo_habitaciones
    if resultado.get('tipo_habitaciones'):
        tipo_str = resultado['tipo_habitaciones'].lower()
        
        # Normalizar caracteres
        tipo_str = (tipo_str
            .replace('á', 'a')
            .replace('é', 'e')
            .replace('í', 'i')
            .replace('ó', 'o')
            .replace('ú', 'u'))
        
        resultado['tipo_habitaciones'] = tipo_str
    
    return resultado

def extraccion_fallback(mensaje):
    """Extracción básica sin IA cuando falla la API"""
    import re
    
    mensaje_lower = mensaje.lower()
    
    # Normalizar caracteres
    mensaje_lower = (mensaje_lower
        .replace('á', 'a')
        .replace('é', 'e')
        .replace('í', 'i')
        .replace('ó', 'o')
        .replace('ú', 'u'))
    
    resultado = {
        "check_in": None,
        "check_out": None,
        "cant_personas": None,
        "cantidad_habitaciones": None,
        "tipo_habitaciones": None
    }
    
    # Intentar extraer cantidad de personas
    personas_patterns = [
        r'(\d+)\s*persona',
        r'para\s+(\d+)',
        r'somos\s+(\d+)'
    ]
    
    for pattern in personas_patterns:
        match = re.search(pattern, mensaje_lower)
        if match:
            resultado['cant_personas'] = match.group(1)
            break
    
    # Intentar extraer habitaciones
    habitaciones_patterns = [
        r'(\d+)\s*habitaci',
        r'(\d+)\s*cuarto',
        r'(\d+)\s*pieza'
    ]
    
    for pattern in habitaciones_patterns:
        match = re.search(pattern, mensaje_lower)
        if match:
            resultado['cantidad_habitaciones'] = match.group(1)
            break
    
    # Si no encontró habitaciones pero encontró personas, asumir 1 habitación
    if resultado['cant_personas'] and not resultado['cantidad_habitaciones']:
        resultado['cantidad_habitaciones'] = '1'
    
    # Detectar tipos de habitaciones
    tipos = []
    
    if 'single' in mensaje_lower or 'sencilla' in mensaje_lower:
        tipos.append('single')
    if 'estandar' in mensaje_lower or 'standard' in mensaje_lower:
        tipos.append('estandar')
    if 'superior' in mensaje_lower:
        tipos.append('superior')
    if 'doble' in mensaje_lower:
        tipos.append('doble')
    
    if tipos:
        resultado['tipo_habitaciones'] = ', '.join(tipos)
    
    # Intentar detectar fechas con "mañana", "hoy", etc.
    fecha_actual = datetime.now()
    
    if 'manana' in mensaje_lower or 'mañana' in mensaje_lower:
        resultado['check_in'] = (fecha_actual + timedelta(days=1)).strftime('%Y-%m-%d')
        resultado['check_out'] = (fecha_actual + timedelta(days=2)).strftime('%Y-%m-%d')
    elif 'hoy' in mensaje_lower:
        resultado['check_in'] = fecha_actual.strftime('%Y-%m-%d')
        resultado['check_out'] = (fecha_actual + timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'pasado manana' in mensaje_lower:
        resultado['check_in'] = (fecha_actual + timedelta(days=2)).strftime('%Y-%m-%d')
        resultado['check_out'] = (fecha_actual + timedelta(days=3)).strftime('%Y-%m-%d')
    
    # Intentar detectar rangos de fechas (del X al Y)
    rango_pattern = r'del\s+(\d+)\s+al\s+(\d+)'
    match = re.search(rango_pattern, mensaje_lower)
    
    if match:
        dia_inicio = int(match.group(1))
        dia_fin = int(match.group(2))
        
        mes_actual = fecha_actual.month
        año_actual = fecha_actual.year
        
        # Si el día ya pasó este mes, asumir mes siguiente
        if dia_inicio < fecha_actual.day:
            mes_actual += 1
            if mes_actual > 12:
                mes_actual = 1
                año_actual += 1
        
        try:
            resultado['check_in'] = f"{año_actual}-{mes_actual:02d}-{dia_inicio:02d}"
            resultado['check_out'] = f"{año_actual}-{mes_actual:02d}-{dia_fin:02d}"
        except:
            pass
    
    print(f"⚠️ Usando extracción fallback: {resultado}")
    return resultado