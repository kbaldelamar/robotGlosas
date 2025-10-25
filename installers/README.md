# Carpeta de Instaladores

## Tesseract OCR

Para habilitar la instalación automática de Tesseract OCR, coloque el archivo instalador en esta carpeta:

### Archivo requerido:
- **Nombre:** `tesseract-ocr-w64-setup-*.exe` (cualquier versión)
- **Origen:** https://github.com/UB-Mannheim/tesseract/wiki
- **Versión recomendada:** 5.3.3 o superior

### ¿Cómo obtener el instalador?

1. **Ir a:** https://github.com/UB-Mannheim/tesseract/wiki
2. **Descargar:** El archivo `.exe` para Windows 64-bit
3. **Copiar** el archivo a esta carpeta (`installers/`)
4. **Listo:** La aplicación lo detectará automáticamente

### Detección automática

La aplicación buscará automáticamente instaladores en:
- ✅ Esta carpeta (`installers/`)
- ✅ Directorio raíz del proyecto
- ✅ Carpeta de descargas del usuario
- ✅ Escritorio del usuario

### Nombres de archivo detectados:
- `tesseract*.exe`
- `Tesseract*.exe`
- `*tesseract*.exe`

### Funcionamiento

Cuando el usuario intente usar OCR y Tesseract no esté instalado:

1. **Detección:** La aplicación busca instaladores locales
2. **Opción:** Ofrece instalación automática o descarga desde internet
3. **Instalación:** Ejecuta instalación silenciosa
4. **Configuración:** Configura automáticamente la ruta
5. **Verificación:** Confirma que funciona correctamente

### Si no hay instalador local:

La aplicación puede descargar automáticamente desde:
```
https://github.com/UB-Mannheim/tesseract/releases/
```

---

## Otros instaladores futuros

Esta carpeta también puede usarse para otros componentes que la aplicación pueda necesitar en el futuro.