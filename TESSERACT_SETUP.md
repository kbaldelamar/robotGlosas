# Configuración de Tesseract OCR para Windows

## ¿Qué es Tesseract OCR?
Tesseract es un motor de reconocimiento óptico de caracteres (OCR) que permite extraer texto de imágenes. 
Es necesario para que el Separador de PDF pueda identificar números de documento en las páginas.

## Instalación en Windows

### Opción 1: Descarga Directa (Recomendada)
1. Descargar desde: https://github.com/UB-Mannheim/tesseract/wiki
2. Ejecutar el instalador (.exe)
3. Instalar en la ruta por defecto: `C:\Program Files\Tesseract-OCR\`
4. **IMPORTANTE**: Agregar al PATH de Windows:
   - Abrir "Variables de entorno"
   - Agregar `C:\Program Files\Tesseract-OCR` al PATH
   - Reiniciar VS Code/aplicación

### Opción 2: Con Chocolatey
```powershell
choco install tesseract
```

### Opción 3: Con Scoop
```powershell
scoop install tesseract
```

## Verificación de Instalación

Abrir terminal y ejecutar:
```powershell
tesseract --version
```

Debería mostrar información de la versión instalada.

## Configuración en Python

Si Tesseract no se encuentra automáticamente, agregar al código:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## Paquetes de Idioma (Opcional)

Para mejor reconocimiento en español:
1. Descargar `spa.traineddata` desde: https://github.com/tesseract-ocr/tessdata
2. Colocar en: `C:\Program Files\Tesseract-OCR\tessdata\`
3. Usar en código: `pytesseract.image_to_string(img, lang='spa')`

## Solución de Problemas

### Error: "TesseractNotFoundError"
1. Verificar que Tesseract esté instalado
2. Comprobar PATH de Windows
3. Reiniciar aplicación/terminal
4. Configurar ruta manualmente en código

### Error: Calidad de OCR baja
1. Usar imágenes de mayor resolución
2. Aplicar preprocesamiento de imagen
3. Configurar parámetros específicos de Tesseract
4. Usar paquetes de idioma apropiados

### Configuración específica para documentos de identidad:
```python
custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
text = pytesseract.image_to_string(image, config=custom_config)
```

## Alternativas si Tesseract falla

El Separador de PDF puede funcionar sin OCR:
- Los archivos se nombrarán con número de página únicamente
- Formato: `pagina_001.pdf`, `pagina_002.pdf`, etc.
- Dejar la opción "Usar OCR" desmarcada

## Enlaces Útiles

- Documentación oficial: https://tesseract-ocr.github.io/
- Instaladores Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Paquetes de idioma: https://github.com/tesseract-ocr/tessdata
- Guía de configuración: https://pypi.org/project/pytesseract/