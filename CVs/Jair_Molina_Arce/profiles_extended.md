# Perfiles Extendidos de Jair Molina Arce (Objetivo: 2 Páginas por CV)

## Información General para todos los CVs
**Nombre**: Jair Molina Arce
**Ubicación**: Querétaro, Qro., México
**Contacto**: ingjairmolina@gmail.com | 5652646108 | jairmolina.dev | github.com/smookymolina | linkedin.com/in/jair-molina-arce-4909622b2
**Educación**:
- **Maestría en Tecnologías Avanzadas** (2024 -- Presente), Instituto Politécnico Nacional (IPN). 
  - Línea de investigación principal: control de sistemas dinámicos e instrumentación.
  - Cursos destacados: Control Avanzado, Procesamiento de Señales, Instrumentación Virtual.
  - Desarrollo de tesis enfocada en la optimización de sistemas de control aplicados a bancos de prueba.
- **Ingeniería Mecánica** (2017 -- 2023), Instituto Politécnico Nacional (IPN). 
  - Enfoque en diseño de bancos de prueba, térmica, instrumentación y sistemas embebidos.
  - Participación activa en proyectos extracurriculares de diseño mecánico y manufactura.
  - Proyecto terminal destacado en caracterización térmica y estructural de componentes aeroespaciales.
- **Bachillerato Técnico en Informática** (2014 -- 2017), Colegio de Bachilleres Plantel 1 "El Rosario".
  - Fundamentos de programación, bases de datos y mantenimiento de equipo de cómputo.

**Idiomas**: Español (Nativo) | Inglés (Avanzado, con lectura técnica fluida y capacidad de redacción de reportes de ingeniería).

**Competencias Transversales (Soft Skills)**: Liderazgo técnico, resolución de problemas complejos, capacidad de análisis crítico, trabajo en equipo multidisciplinario, comunicación efectiva de conceptos técnicos a audiencias no técnicas, adaptabilidad, aprendizaje continuo, gestión del tiempo y organización de proyectos.

---

## Profile 1: Embedded Systems Junior CV
**Título**: Ingeniero en Sistemas Embebidos Jr.
**Perfil Profesional**: Ingeniero Mecánico con sólida formación orientada a sistemas embebidos, instrumentación y control. He desarrollado firmware escalable y robusto para plataformas como ESP32, STM32 y RP2350 utilizando C/C++, MicroPython y Arduino framework. Mi experiencia incluye la integración de periféricos (ADC, PWM, timers), implementación de mecanismos de seguridad (watchdog), diseño de máquinas de estados (FSM) y sistemas de adquisición de datos (DAQ). Mi perfil es único porque combina un profundo criterio mecánico con electrónica práctica y documentación técnica rigurosa; me siento completamente cómodo depurando sistemas físicos con osciloscopio, multímetro, analizador lógico, consola serial y simuladores de hardware. Busco un rol junior en el que pueda aportar autonomía técnica, orden, metodologías de desarrollo estructuradas y una base sólida para crecer en áreas de firmware, integración de hardware mixed-signal y validación de sistemas críticos.

**Habilidades Técnicas**:
- **Firmware / Software**: C/C++, MicroPython, Python, PlatformIO, Arduino framework, Máquinas de Estados (FSM), ADC, PWM, Timers, Watchdog, depuración serial, REPL, fundamentos de JTAG/SWD, memory mapping, bare-metal, conceptos fundamentales de RTOS, ISR (Interrupt Service Routines), logging, manejo de errores, y optimización en entornos de memoria limitada.
- **Microcontroladores y Arquitecturas**: ESP32, STM32, RP2040, RP2350, configuración de bajo nivel de GPIOs y periféricos, integración de sensores y actuadores, diseño de software orientado a seguridad y estados fail-safe.
- **Protocolos de Comunicación**: UART, SPI, I2C, MQTT, HTTP/REST, WiFi (configuración de modos STA/AP).
- **Hardware e Instrumentación**: DAQ, lectura de NTCs, acondicionamiento de señales analógicas, control de ventilación, drivers de motores (TB6612FNG), MOSFET de potencia, reguladores LDO, diseño de layout mixed-signal, implementaciones de protecciones eléctricas, uso de osciloscopio, multímetro, validación y testing de hardware.
- **Herramientas CAD/CAE y Datos**: KiCad, SolidWorks, ANSYS, MATLAB/Simulink, LabVIEW, procesamiento de datos con pandas, numpy, visualización con matplotlib, control de versiones con Git.

**Experiencia Relevante**:
- **Docente Universitario - Ingeniería Térmica y Modelización de Sistemas Aeroespaciales** | Universidad Internacional de Innovación de Aguascalientes | Ago. 2025 -- Presente.
  - Imparto clases de nivel licenciatura y desarrollo material técnico avanzado con foco en modelado, análisis de sistemas y resolución estructurada de problemas de ingeniería.
  - Aplico herramientas de simulación computacional para explicar fenómenos térmicos y dinámicos a nivel académico y profesional.
  - Traduzco conceptos complejos de física, matemáticas e ingeniería a material claro, con estructura útil para alumnos y equipos técnicos.
  - Implementación de rúbricas de evaluación técnica y fomento del pensamiento crítico.
- **Sistemas Embebidos e Instrumentación - Banco de Pruebas de Propulsión** | Instituto Politécnico Nacional (IPN) | 2022 -- 2024.
  - Diseñé, construí e implementé un sistema DAQ personalizado con sensores de presión, temperatura y flujo para un banco de pruebas de cohetes de combustible sólido.
  - Programé microcontroladores ESP32 y STM32 para la lectura sincronizada de sensores, transmisión de datos de alta velocidad y control preciso de actuadores.
  - Integré buses de comunicación UART, SPI e I2C según los requerimientos específicos de ancho de banda y distancia del banco.
  - Analicé señales y resultados experimentales utilizando Python, MATLAB/Simulink y LabVIEW.
  - Documenté exhaustivamente ensayos, variables de calibración y criterios de validación para garantizar la repetibilidad de las pruebas y la trazabilidad de los resultados.
  - Lideré la selección de instrumentación y el diseño de protocolos de seguridad operacional.

**Proyecto Embebido Destacado**:
- **Jaguar MX - Sistema de Extracción de Aire Caliente para Gabinete de Telecomunicaciones** (2026).
  - *Rol*: Desarrollo completo (firmware, simulación, esquemático y PCB) usando Seeed XIAO RP2350 / RP2040-Wokwi.
  - Diseñé y validé una FSM de seguridad robusta (INIT -> READING -> COOLING/IDLE/ERROR/LOCKOUT) con watchdog de hardware de 8 segundos, asegurando un estado seguro por falla y recuperación controlada.
  - Implementé adquisición de temperatura mediante 2 sensores NTC TT05 con divisor de voltaje, conversión Beta, validación de estado abierto/corto y filtro digital trimmed-mean sobre un buffer circular.
  - Integré un DIP switch para selección de 8 setpoints térmicos y apliqué una histéresis de +/-1 °C para evitar chattering electromecánico.
  - Controlé el actuador FIT0803 y el ventilador industrial MR1238E48B-FSR mediante puente H y MOSFET de potencia aislados.
  - Separé meticulosamente el diseño analógico y de potencia en KiCad, optimizando rutas de ADC y utilizando planos de tierra divididos (net-ties).

**Proyectos Seleccionados**:
- **Pipeline de Automatización de Análisis de Datos y Reportes** (2024 -- 2025). Construí un flujo en Python (Pandas/NumPy) para procesar grandes volúmenes de datos experimentales con ruido, reduciendo el tiempo de análisis de 6 horas a menos de 20 minutos.
- **Sistema de Telemetría Inalámbrica para Propulsores Cohete** (2023 -- 2024). Desarrollé telemetría de baja latencia con ESP32, backend MQTT y visualización en tiempo real (latencia < 50 ms).
- **Sistema de Control Adaptativo PID con Ajuste Automático** (2023 -- 2024). Implementación en C++ embebido de un controlador PID digital con auto-tuning, reduciendo el tiempo de estabilización térmica en un 35%.

**Freelance y Proyectos Independientes**:
- **Instructor - Excel Avanzado** (Mar. 2026). Diseño e impartición de curso intensivo corporativo cubriendo macros VBA, Power Query y automatización de reportes.
- **Plataforma Web Full-Stack para Monitoreo IoT** (2023 -- 2024). Desarrollo de backend Flask, APIs RESTful, bases de datos relacionales y despliegue con Docker para visualización de sensores remotos.

---

## Profile 2: Mechanical Engineer CV
**Título**: Ingeniero Mecánico
**Perfil Profesional**: Ingeniero Mecánico egresado del IPN, actualmente cursando una maestría en Tecnologías Avanzadas. Poseo experiencia comprobada en diseño mecánico, análisis térmico y estructural mediante Elementos Finitos (FEA), dimensionamiento de bancos de prueba e instrumentación de precisión. He caracterizado, diseñado y simulado sistemas mecánicos complejos utilizando SolidWorks, ANSYS y MATLAB/Simulink, y he validado su comportamiento dinámico mediante sistemas de adquisición de datos y pruebas experimentales rigurosas. Mi principal diferencial competitivo es la capacidad de integrar fluidamente el dominio mecánico con la electrónica y la automatización: logro que sensores, actuadores y microcontroladores trabajen en sinergia como un único sistema electromecánico cohesivo. Busco un rol desafiante en ingeniería mecánica orientado al diseño de producto, gestión térmica avanzada, pruebas de confiabilidad o validación de sistemas.

**Habilidades Técnicas**:
- **Diseño / CAD-CAE**: SolidWorks (Modelado 3D, Ensamblajes, Dibujos técnicos), ANSYS (Análisis FEA estructural, modal y térmico), MATLAB/Simulink (Modelado dinámico), diseño, cálculo y dimensionamiento de bancos de prueba, lectura e interpretación avanzada de planos bajo normas internacionales (GD&T), metrología dimensional, impresión 3D (FDM, SLA) para prototipado rápido.
- **Térmica y Fluidos**: Análisis de transferencia de calor (conducción, convección, radiación), termodinámica aplicada, gestión térmica integral de gabinetes y equipos electrónicos, cálculo y control de sistemas de ventilación, análisis de eficiencia y balance energético de sistemas.
- **Instrumentación y Pruebas**: Adquisición de Datos (DAQ) mediante LabVIEW y Python, selección e implementación de sensores de presión, temperatura (termoacoples, RTDs, NTCs) y flujo, acondicionamiento de señales, estrategias de control PID, calibración de instrumentos, uso de osciloscopio y multímetro, diseño de protocolos de validación experimental y aseguramiento de la trazabilidad metrológica de los ensayos.
- **Mecatrónica y Automatización**: Experiencia práctica con microcontroladores (ESP32, STM32, serie RP), programación en C/C++ y Python, control de motores a pasos (NEMA, drivers A4988), puentes H, selección y dimensionamiento de MOSFETs de potencia, buses de comunicación (UART, SPI, I2C), diseño de PCBs de interconexión básica en KiCad.
- **Datos y Software**: Programación en Python (pandas, numpy, matplotlib para análisis de datos experimentales), Excel nivel avanzado (Power Query, macros VBA), control de versiones con Git, contenerización básica con Docker.

**Experiencia Relevante**:
- **Docente Universitario - Ingeniería Térmica y Modelización de Sistemas Aeroespaciales** | Universidad Internacional de Innovación de Aguascalientes | Ago. 2025 -- Presente.
  - Titular de la materia de Ingeniería Térmica, cubriendo transferencia de calor, termodinámica aplicada y análisis energético de sistemas complejos.
  - Titular de Modelización de Sistemas Aeroespaciales, abarcando dinámica de vuelo, simulación numérica y desarrollo de modelos matemáticos.
  - Diseño integral de material didáctico, evaluaciones prácticas basadas en proyectos y simulaciones computacionales, gestionado 100% en línea.
- **Docente - Tecnologías Disruptivas (Realidad Virtual y Aumentada)** | ENBA - IPN | 2024.
  - Impartí curso de posgrado enfocado en el impacto y aplicación industrial de la VR/AR.
  - Diseñé metodologías para la aplicación de estas tecnologías en la capacitación técnica inmersiva y gestión de información espacial.
- **Ingeniería Mecánica e Instrumentación - Banco de Pruebas de Propulsión** | Instituto Politécnico Nacional (IPN) | 2022 -- 2024.
  - Caractericé, diseñé y simulé la estructura completa de un banco de pruebas mecánicas para cohetes de combustible sólido de investigación.
  - Ejecuté análisis térmico-estructurales (FEA) de componentes críticos, iterando diseños para soportar cargas dinámicas extremas y gradientes térmicos.
  - Implementé el sistema DAQ (LabVIEW, Python) logrando una captura de datos de alta fidelidad, vital para la validación de las simulaciones teóricas.
  - Trabajo de investigación publicado formalmente en *Revista Hacia el Espacio* (2024).

**Proyecto Mecánico Destacado**:
- **Jaguar MX - Sistema de Extracción de Aire Caliente para Gabinete de Telecomunicaciones** (2026).
  - *Rol*: Diseño conceptual, gestión térmica, selección de componentes mecánicos/eléctricos y validación de prototipo.
  - Desarrollé la estrategia completa de disipación térmica del gabinete, estableciendo curvas de operación para extracción de aire caliente.
  - Calculé flujos de aire requeridos y seleccioné el ventilador industrial MR1238E48B-FSR (48 V) y actuadores de compuerta óptimos.
  - Instrumenté la medición de temperatura en puntos críticos para garantizar que los equipos de telecomunicaciones operen dentro de su envolvente térmica segura.
  - Diseñé el layout de los componentes para maximizar el flujo de aire y minimizar la recirculación de aire caliente, modelando escenarios en software.

**Proyectos Seleccionados**:
- **Impresora 3D DIY - Diseño y Construcción desde Cero**. Diseño íntegro de la estructura mecánica, sistema cinemático CoreXY en SolidWorks, análisis estructural del chasis en aluminio extruido, e integración mecatrónica (Arduino Mega, motores NEMA 17). Cierre del ciclo diseño-manufactura-validación con la impresión exitosa de piezas de prueba dimensionales.
- **Pipeline de Automatización de Análisis de Datos y Reportes** (2024 -- 2025). Reducción del tiempo de análisis post-prueba en un 90% mediante rutinas automáticas que consolidan datos de múltiples sensores en reportes técnicos listos para auditoría.
- **Sistema de Control Adaptativo PID con Ajuste Automático** (2023 -- 2024). Modelado matemático de una planta térmica en MATLAB y validación práctica de algoritmos de control.

**Freelance e Investigación**:
- **Producción Científica**: Ponente y coautor en el *75th International Astronautical Congress (IAC 2024)*, Milán, Italia (DOI: 10.52202/078365-0120). Publicación en *Revista Hacia el Espacio* (2024). CVU CONACYT: 1340773 | ORCID: 0009-0009-6732-8100.
- **Instructor - Excel Avanzado** (Mar. 2026). Automatización de flujos de información técnica y financiera.

---

## Profile 3: General CV (Ingeniero Mecánico y Embebidos)
**Título**: Ingeniero Mecánico y de Sistemas Embebidos
**Perfil Profesional**: Ingeniero Mecánico multidisciplinario con sólida experiencia transversal que abarca el diseño mecánico avanzado, el desarrollo de hardware (PCBs) y la programación de firmware de bajo nivel para sistemas embebidos. Mi trayectoria profesional incluye la caracterización detallada de bancos de prueba de propulsión, la ejecución de simulaciones térmicas y estructurales complejas (FEA), y la automatización integral de procesos físicos mediante microcontroladores (ESP32, STM32, arquitecturas ARM Cortex). Destaco en el sector por mi capacidad excepcional para actuar como puente tecnológico: integro fluidamente requerimientos mecánicos con soluciones electrónicas y de software, desarrollando productos desde la fase de diseño conceptual (CAD), pasando por el prototipado rápido y el diseño de circuito impreso, hasta llegar a la validación física del hardware final y su puesta en marcha.

**Habilidades Técnicas Integrales**:
- **Diseño Mecánico y Simulación**: Dominio de SolidWorks para modelado 3D de piezas complejas y ensamblajes mayores; análisis por Elementos Finitos (FEA) empleando ANSYS para validación estructural bajo cargas estáticas/dinámicas y estrés térmico; modelado matemático en MATLAB/Simulink; metrología e interpretación de tolerancias geométricas (GD&T).
- **Desarrollo de Firmware y Electrónica**: Programación en C/C++ y MicroPython; arquitectura de software embebido (máquinas de estado, interrupciones, manejo de memoria); diseño de PCBs mixed-signal utilizando KiCad con enfoque en integridad de señal e inmunidad al ruido electromagnético; integración de periféricos (ADC, DAC, PWM) y buses (I2C, SPI, UART).
- **Instrumentación y Control**: Diseño de sistemas DAQ (Adquisición de Datos); selección, calibración y acondicionamiento de sensores (temperatura, presión, celdas de carga); implementación y sintonización de lazos de control PID; manejo competente de equipo de laboratorio (osciloscopios, generadores de funciones, fuentes de poder).
- **Software, Datos y Gestión**: Desarrollo de scripts en Python (Pandas, NumPy) para automatización de análisis de datos experimentales; desarrollo web backend (Flask); control de versiones (Git); uso de Docker para entornos aislados; redacción técnica y documentación de ingeniería.

**Experiencia Relevante**:
- **Docente Universitario e Investigador** | Instituciones Privadas y Públicas (IPN) | 2024 -- Presente.
  - Impartición de cátedras en Ingeniería Térmica, Modelización de Sistemas Aeroespaciales y Tecnologías Disruptivas.
  - Desarrollo continuo de investigación en el área de control de sistemas dinámicos e instrumentación avanzada.
  - Autoría de artículos técnicos y presentaciones en foros internacionales de ingeniería aeroespacial.
- **Ingeniería y Desarrollo Integrado - Banco de Pruebas de Propulsión** | Instituto Politécnico Nacional | 2022 -- 2024.
  - Ejecuté el ciclo completo de diseño de una instalación experimental para motores cohete: desde el diseño CAD del soporte de empuje, hasta la selección de galgas extensiométricas y la programación del DAQ.
  - Implementé rutinas de seguridad automatizadas mediante relés de estado sólido y electroválvulas controladas por STM32.
  - Reduje drásticamente la incertidumbre de medición aplicando técnicas de filtrado digital directamente en el firmware.
  - Consolidé una arquitectura de red local para la transmisión de datos críticos en tiempo real hacia la estación de control.

**Proyectos Destacados (Ciclo de Desarrollo Completo)**:
- **Jaguar MX - Sistema de Extracción de Aire Caliente para Gabinete de Telecomunicaciones** (2026).
  - Desarrollo end-to-end de un sistema de gestión térmica industrial. Inicié con el cálculo de cargas térmicas y diseño CAD para el montaje de ventiladores y ductos. Posteriormente, diseñé el hardware (esquemático y PCB en KiCad) aislando la lógica de baja tensión del puente H de potencia. Finalmente, programé el firmware en C++ asegurando un funcionamiento ininterrumpido mediante watchdogs de hardware y máquinas de estados robustas contra fallos de sensores.
- **Impresora 3D DIY - Diseño Mecatrónico desde Cero**. 
  - Proyecto integral que combinó el diseño CAD del pórtico, análisis de deflexiones, selección de perfiles estructurales, cableado eléctrico del cuadro de control, flasheo y configuración de firmware Marlin, y calibración final de pasos por milímetro e interpolación térmica del hotend.
- **Sistema de Telemetría Inalámbrica y Control Adaptativo PID**.
  - Desarrollo de un nodo sensor portátil con comunicación WiFi/MQTT, operando con baterías Li-Po. Implementación de algoritmos de control adaptativo para compensar variaciones de inercia térmica en tiempo real, mejorando la respuesta del sistema frente a perturbaciones externas.
- **Pipeline de Automatización de Análisis de Datos de Ingeniería**.
  - Software propietario desarrollado en Python que procesa archivos de registro (logs) generados durante pruebas destructivas, detecta anomalías, aplica filtros de media móvil y genera automáticamente reportes ejecutivos en formato PDF y hojas de cálculo con gráficos interactivos.

**Educación**:
- **Maestría en Tecnologías Avanzadas** (En curso) - IPN.
- **Ingeniería Mecánica** (2017 -- 2023) - IPN.
- **Bachillerato Técnico en Informática** (2014 -- 2017) - Colegio de Bachilleres.

**Idiomas y Reconocimientos**:
- **Idiomas**: Español (Nativo), Inglés (Avanzado, B2/C1 técnico).
- **Publicaciones**: Coautor presentado en el *75th IAC 2024* (Italia). Artículo en *Revista Hacia el Espacio*.
