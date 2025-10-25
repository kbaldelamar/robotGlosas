# BootGestor v2.2 - Separador de PDF con Instalación Automática de OCR

## Nuevas Características v2.2

### 📄 Separador de PDF Completo
- ✅ División automática de PDF página por página
- ✅ OCR integrado para identificar números de documento
- ✅ **Instalación automática de Tesseract OCR**
- ✅ Nomenclatura automática de archivos
- ✅ Progreso en tiempo real y logs detallados

### 🔧 Instalación Automática de Tesseract

#### Funcionamiento Automático:
1. **Detección:** La aplicación detecta si Tesseract está instalado
2. **Búsqueda local:** Busca instaladores en carpetas conocidas
3. **Descarga automática:** Si no encuentra local, descarga desde internet
4. **Instalación silenciosa:** Instala automáticamente sin intervención
5. **Configuración:** Configura automáticamente la ruta

#### Ubicaciones de búsqueda para instaladores:
- `installers/` (carpeta del proyecto)
- Directorio raíz del proyecto
- Carpeta de Descargas del usuario
- Escritorio del usuario

#### Descarga automática desde:
```
https://github.com/UB-Mannheim/tesseract/releases/
```

### 🚀 Cómo Usar el Separador de PDF

1. **Abrir módulo:** Menú → Módulos → "📄 Separador de PDF"
2. **Seleccionar PDF:** Archivo a dividir
3. **Seleccionar carpeta:** Donde guardar páginas separadas
4. **Configurar OCR:** Mantener habilitado para identificar documentos
5. **Iniciar:** Si no tiene Tesseract, se instalará automáticamente

### 📋 Archivos Generados

#### Con OCR (recomendado):
```
documento_48162593_pagina_001.pdf
documento_12345678_pagina_002.pdf
documento_87654321_pagina_003.pdf
```

#### Sin OCR:
```
documento_SIN_IDENTIFICAR_pagina_001.pdf
documento_SIN_IDENTIFICAR_pagina_002.pdf
documento_SIN_IDENTIFICAR_pagina_003.pdf
```

### ⚙️ Configuración Avanzada

#### Rangos de páginas:
- Página inicial: 1 (por defecto)
- Página final: 999 = "Hasta el final"

#### Configuración OCR:
- Automática: La aplicación maneja todo
- Manual: Instalar Tesseract desde https://github.com/UB-Mannheim/tesseract/wiki

### 🛠️ Scripts de Ayuda Incluidos

#### `descargar_tesseract.bat`
- Descarga automática de Tesseract
- Verificación de instalación
- Enlaces a descarga manual

#### `instalar_pdf_deps.bat`
- Instala todas las dependencias de PDF
- PyPDF2, Pillow, PyMuPDF, pytesseract

### 🔍 Solución de Problemas

#### "Tesseract no encontrado":
1. La aplicación ofrecerá instalación automática
2. Si falla, use `descargar_tesseract.bat`
3. O descargue manualmente desde GitHub

#### "Error de instalación":
1. Ejecutar como Administrador
2. Verificar conexión a internet
3. Descargar instalador manualmente

#### OCR no funciona:
1. Verificar que Tesseract esté en PATH
2. Reiniciar la aplicación
3. Usar "Verificar instalación" en el script

### 📦 Dependencias Instaladas Automáticamente

```
PyPDF2==3.0.1          # División de PDF
pytesseract==0.3.10     # Interface OCR
Pillow==10.1.0          # Procesamiento de imágenes  
PyMuPDF==1.23.14        # Conversión PDF a imagen
urllib3>=1.26.0         # Descarga de archivos
```

### 🏗️ Arquitectura Técnica

#### Componentes:
- `PDFSeparatorWidget`: Interfaz principal
- `PDFSeparatorThread`: Procesamiento en segundo plano
- `TesseractManager`: Gestión de instalación OCR
- `TesseractDownloadThread`: Descarga/instalación asíncrona

#### Flujo de trabajo:
1. **UI**: Selección de archivos y configuración
2. **Verificación**: Comprobar disponibilidad de Tesseract
3. **Instalación**: Si es necesario, instalar automáticamente
4. **Procesamiento**: Dividir PDF página por página
5. **OCR**: Extraer números de documento de cada página
6. **Nomenclatura**: Nombrar archivos automáticamente

### 📄 Ejemplo de Uso Real

Para un PDF con capturas de pantalla del sistema COOSALUD:

#### Entrada:
- `PDF_CASOS_GLOSAS.pdf` (50 páginas)

#### Salida:
```
documento_48162593_pagina_001.pdf  # Ana Yolanda Díaz
documento_12345678_pagina_002.pdf  # Otro paciente
documento_87654321_pagina_003.pdf  # Otro paciente
...
```

#### Log en tiempo real:
```
📁 PDF seleccionado: PDF_CASOS_GLOSAS.pdf
📂 Carpeta de salida: C:/miCrud/biomed/pdf separados
🚀 Iniciando separación de PDF...
📄 Página 1: ✅ Documento 48162593
📄 Página 2: ✅ Documento 12345678
📄 Página 3: ✅ Documento 87654321
✅ Separación completada exitosamente!
```

### 🎯 Casos de Uso

1. **Procesamiento de glosas médicas**
2. **Separación de documentos escaneados**
3. **Organización de archivos por paciente**
4. **Preparación de documentos para sistemas automatizados**

### 🔗 Enlaces Útiles

- **Tesseract OCR:** https://github.com/UB-Mannheim/tesseract/wiki
- **PyPDF2 Docs:** https://pypi.org/project/PyPDF2/
- **Pytesseract:** https://pypi.org/project/pytesseract/