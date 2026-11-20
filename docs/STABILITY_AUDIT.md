# Estabilización de Arquitectura ARUS

Base `3091a37`. Este incremento cubre la política de herramientas y la
propiedad del proceso Ollama. La preparación de ARUS 1.0 continúa abierta.

| Prioridad | Hallazgo | Estado |
| --- | --- | --- |
| P0 | La herramienta de shell enviaba al intérprete texto originado en el modelo. | Sustituida por cuatro operaciones nativas sin crear procesos. Pruebas de operaciones válidas y denegadas. |
| P1 | El despacho exponía al modelo escrituras, red, ejecución indirecta y herramientas añadidas desde plugins. | Denegación por defecto en el despachador y esquemas limitados. El flujo de confirmación humana para habilitar otras herramientas sigue pendiente. |
| P1 | Los puntos de entrada activos terminaban Ollama mediante señales globales. | Solo se controla el proceso hijo del que la instancia conserva una referencia. Pruebas con proceso simulado y puerto existente. Los archivos históricos se conservan como referencia. |
| P1 | La validación original de rutas estaba separada de la apertura y los límites eran inconsistentes. | Lectura y escritura por descriptores de directorio en Linux, sin seguir enlaces simbólicos, con límite de 256 KiB y escritura por reemplazo atómico. |
| P2 | El ejecutor explícito de pruebas detectaba pytest en un intérprete y ejecutaba otro. | Usa `sys.executable`. La comprobación funcional original volvía a pasar. |
| P2 | La configuración, módulos de red, plugins, datos históricos, tareas persistentes y proveedores fuera de Ollama requieren revisión específica. | Pendiente. Los archivos de datos versionados no se migraron ni se modificaron. |
| P3 | Dependencias de voz, visión y plataformas adicionales necesitan pruebas de despliegue. | Pendiente. |

## Verificación

Se instalaron dependencias en un entorno virtual de Python 3.13.5 y se
ejecutaron las pruebas en copias aisladas. La base pasó 28 pruebas. En la
evaluación base pasaron 26 comprobaciones, falló el ejecutor de pruebas por
usar el intérprete global y se omitieron cuatro comprobaciones.

`python -m pytest -q tests learning/tests` pasó 33 pruebas. `evaluation.suite.run_all()`
devolvió 27 aprobadas, cero fallos y cuatro omitidas. Las omitidas corresponden
a acceso web, búsqueda web, fallo de conexión con Ollama y disponibilidad de
visión. La ventana PySide6 abrió y cerró con `QT_QPA_PLATFORM=offscreen` y el
proveedor desactivado. El ciclo de vida de Ollama se verificó con dobles de prueba.

El próximo incremento debe validar los destinos de todos los proveedores,
manejar timeout y cancelación, y comprobar el flujo con un proveedor local
real. La aprobación humana en la UI, las políticas de plugins, la migración de
datos y la CI de release siguen pendientes.
