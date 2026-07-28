# Interfaz profesional MercadoBot Personal OS 0.5

## Diseño activo

La interfaz utiliza como tema principal:

- fondo principal `#07111F`;
- barras y encabezados `#0A1628`;
- tarjetas `#101F33`;
- paneles elevados `#162A42`;
- títulos `#F5F7FA`;
- textos secundarios `#CBD5E1` y `#8291A6`;
- positivo `#22C55E`;
- negativo real `#EF4444`;
- acciones `#3B82F6`;
- arbitraje y liquidez `#14B8A6`;
- objetivos y cuentas próximas `#F5B942`;
- inteligencia, memoria y patrones `#8B5CF6`.

También incluye modo claro y temas negro-dorado, gris profesional y azul claro. Los temas no cambian el significado financiero de positivo y negativo.

## Estructura

- barra lateral fija y contraíble;
- barra superior con búsqueda, capital, rendimiento, hora, sincronización, cuenta, tema, perfil y acceso rápido;
- área central adaptable;
- panel derecho contextual que puede contraerse;
- navegación inferior para móviles.

## Vistas

- Inicio;
- Portafolio;
- Centro de arbitraje;
- Oportunidades;
- Estrategias y constructor visual;
- Memoria de mercado;
- Operaciones;
- Planificación de capital;
- Calendario;
- Cuentas regresivas;
- Horarios claves;
- Estadísticas;
- Simulaciones;
- Reportes;
- Conexiones;
- Configuración.

## Interacción y rendimiento

- carga progresiva de los archivos JSON;
- actualización parcial cada 30 segundos;
- esqueletos de carga;
- buscador global y atajo de teclado;
- tablas con desplazamiento y vistas compactas;
- tarjetas arrastrables con orden guardado localmente;
- paneles laterales para detalles rápidos;
- ventanas centradas solo para acciones extensas;
- preferencias guardadas en `localStorage`;
- animaciones breves y opción de reducir movimiento;
- tamaño de texto y densidad configurables;
- navegación por teclado y etiquetas accesibles.

## Límites honestos de GitHub Pages

GitHub Pages es estático y público. Por tanto:

- no puede proteger datos mediante una pantalla de inicio de sesión puramente visual;
- no puede mantener sesiones privadas seguras;
- no puede escribir operaciones personales en un servidor;
- no puede ejecutar órdenes;
- no puede sincronizar de forma privada entre dispositivos sin un backend.

La interfaz muestra estas capacidades como preparadas y requiere un backend privado autenticado para activarlas. No se incluye una pantalla de acceso falsa que dé una sensación incorrecta de privacidad.

## Integridad del despliegue

Los archivos HTML, CSS, JavaScript y SVG se almacenan en paquetes gzip-base64. `app.frontend_assets` los reconstruye y comprueba su SHA-256 antes de publicar. GitHub Actions cancela el despliegue si falta un recurso, se altera un fragmento o no coincide la suma esperada.
