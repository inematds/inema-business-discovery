# INEMA Business Discovery

[![INEMA Business Discovery](guia/assets/banner-es.jpg)](https://inematds.github.io/inema-business-discovery/guia/es/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## Qué es

INEMA Business Discovery es un programa abierto que lee las planillas de tu empresa (ventas, clientes, propuestas, gastos y operación) y señala oportunidades: clientes que dejaron de comprar, gastos que subieron demasiado, retrabajo, ventas que podrían concretarse. Sirve al dueño o gerente de una pequeña o mediana empresa que quiere decidir con pruebas, no con corazonadas. Cada hallazgo viene con la cuenta, el grado de confianza y una prueba para confirmarlo. Para usarlo, basta con Python 3 y las planillas exportadas en CSV.

## 📖 Guía de uso

Guía completa (landing + paso a paso): **https://inematds.github.io/inema-business-discovery/guia/es/**

**Laboratorio de descubrimientos para la gestión de negocios.** Seis agentes investigan los datos de la empresa, encuentran oportunidades que el gerente todavía no vio, proponen hipótesis, planifican pruebas con grupo de control, verifican las cuentas, intentan derribar sus propias conclusiones y guardan lo aprendido.

> ¿Y si una empresa tuviera un equipo de investigadores de IA trabajando las 24 horas, no para responder las preguntas del gerente, sino para descubrir continuamente cómo puede ganar más, gastar menos y operar mejor?

## En 1 minuto

```bash
git clone https://github.com/inematds/inema-business-discovery
cd inema-business-discovery
python3 -m bd demo                       # empresa FICTICIA, ciclo completo
python3 -m bd servir --saida saida-demo  # panel en http://127.0.0.1:8765
```

Solo necesitas Python 3.10+. Ninguna dependencia externa, ninguna clave de API.

La demo reproduce el ejemplo del documento de visión: **120 clientes inactivos × 20% de conversión × ticket de R$ 3.500 = R$ 84.000 de ingreso potencial; × margen de 30% = R$ 25.200 de contribución potencial.** Es un escenario ilustrativo, con datos inventados — no es un resultado observado. La prueba de la demo también es **simulada**.

## El equipo de agentes

| Agente | Qué hace | En el LOOP-R |
|---|---|---|
| **Investigador** | Recorre los 5 frentes y encuentra patrones, anomalías y oportunidades. Solo cálculo, sin modelo de lenguaje. | Localizar |
| **Científico** | Formula la hipótesis y las intervenciones; pone a competir a 3 agentes con estrategias diferentes. | Proponer |
| **Experimentador** | Simula escenarios (pesimista, base, optimista) y sortea el grupo de prueba y el grupo de control. | Operar |
| **Auditor** | Rehace cada cuenta a partir de los datos de entrada, verifica que los objetivos existan y que haya evidencia. Reprueba lo que no cuadra. | (verificación) |
| **Crítico** | Busca explicaciones alternativas y señales de números inflados; baja la confianza. | (verificación) |
| **Memoria** | Guarda descubrimientos, decisiones (quién, cuándo) y lecciones. Solo la estrategia validada se promueve. | Reforzar |

El **Validador** compara lo previsto × lo medido usando el grupo de control — LOOP-R: Observar.
Regla del LOOP-R: **quien hace nunca es quien evalúa.**

## Los cinco frentes

| Frente | Qué busca (en esta versión) |
|---|---|
| Ingresos perdidos | clientes que dejaron de comprar; propuestas olvidadas en el CRM |
| Gastos evitables | gastos recurrentes que subieron más del 10%; dos proveedores para lo mismo |
| Riesgo de abandono | clientes activos que tardan más de lo normal en volver |
| Ineficiencias operativas | etapa que concentra el retrabajo; cuello de botella de tiempo |
| Oportunidades comerciales | productos que se compran juntos (venta cruzada); artículos con margen muy bajo |

Cada descubrimiento sale con: origen de los datos, período, hipótesis, evidencias, cuenta reproducible, supuestos, riesgos, grado de confianza, costo, prioridad y siguiente paso.

## Agentes compitiendo, evaluador a ciegas

Para cada descubrimiento, tres agentes proponen caminos (ej.: **A Recuperación** — contacto personalizado; **B Oferta** — descuento segmentado; **C Relación** — beneficio sin tocar el precio). El evaluador recibe las propuestas mezcladas como "Propuesta 1, 2, 3", sin saber quién hizo cada una, y las puntúa por la contribución neta con descuento de riesgo. La autoría solo se revela después. Una estrategia ya validada en las pruebas gana un bono en las rondas siguientes.

## Gobernanza: la persona aprueba

Contacto comercial, descuento, precio, contrato y cambio de proceso **solo avanzan con la aprobación de una persona** (`python3 -m bd aprovar ID --por "Nome"` o el botón del panel). Un agente no aprueba: nombres como "agente" o "ciclo" se rechazan. Sin aprobación, el Validador se niega a validar. Todo queda en el registro de decisiones.

## Usar con tus datos

Exporta planillas del CRM, del sistema financiero y de la operación a una carpeta (se aceptan `;` o `,`, fechas `aaaa-mm-dd` o `dd/mm/aaaa`, valores `1.234,56`):

> **Importante:** los nombres de archivos, de columnas y las claves del `config.json` deben quedar en portugués tal como aparecen (`vendas.csv`, `cliente_id`, `valor`, `margem_contribuicao`…), porque es lo que la herramienta lee.

| Archivo | Columnas |
|---|---|
| `vendas.csv` (obligatorio) | venda_id, data, cliente_id, produto_id, quantidade, valor |
| `clientes.csv` | cliente_id, nome, segmento, cidade, desde |
| `produtos.csv` | produto_id, nome, categoria, preco, custo |
| `propostas.csv` | proposta_id, cliente_id, data, valor, status, ultimo_contato |
| `despesas.csv` | data, fornecedor, categoria, valor, recorrente, contrato_fim |
| `operacao.csv` | pedido_id, data, etapa, horas, retrabalho |

Un archivo que falta solo desactiva el frente correspondiente. Los supuestos (margen, conversiones, costo por hora) van en un `config.json` en la misma carpeta — mira `exemplos/empresa-ficticia/config.json` y `bd/config.py`.

## El proceso, de principio a fin

🧠 sesión con el gerente · ⚙️ script · 🤖 agente/modelo

1. 🧠 **Exportar los datos** del CRM, del sistema financiero y de la operación a una carpeta (CSV). Sin integración en el primer piloto.
2. 🧠 **Escribir los supuestos** en el `config.json`: margen de contribución, conversiones esperadas, costo por hora.
3. ⚙️ **Ejecutar el ciclo**: `python3 -m bd analisar --dados minha-pasta --saida saida` — Investigador, Científico, Experimentador, Auditor y Crítico se ejecutan en secuencia.
4. 🤖 *(opcional)* **Narrativa**: con `--llm` y `"llm": {"provedor": "ollama"}` en el config, un modelo local explica cada descubrimiento en lenguaje sencillo.
5. 🧠 **Leer el informe** (`saida/relatorio.html`) o abrir el panel: `python3 -m bd servir --saida saida`.
6. 🧠 **Aprobar o rechazar** cada prueba: `python3 -m bd aprovar RP-REATIVACAO --por "Tu Nombre"`.
7. 🧠 **Ejecutar la prueba** con los grupos sorteados en `saida/planos/<ID>-grupos.csv` (solo el grupo "teste" recibe la acción).
8. 🧠 **Registrar el resultado** en CSV: `alvo_id, grupo, converteu, receita`.
9. ⚙️ **Validar**: `python3 -m bd validar RP-REATIVACAO --resultados resultado.csv --saida saida` — calcula la contribución incremental, el valor p y la precisión de la predicción.
10. ⚙️ **Reforzar**: la estrategia que pasó (p < 0,05 y ganancia incremental) se convierte en lección promovida y gana peso en el siguiente ciclo; el resto queda registrado como descartado.
11. ⚙️ **Repetir** cada semana con datos nuevos (cron, systemd o n8n — `n8n/business-discovery.json`). Las decisiones humanas anteriores se conservan.

## Métricas para demostrar resultados

`python3 -m bd memoria --saida saida` muestra: oportunidades validadas, impacto incremental medido, precisión de las hipótesis (previsto × realizado), pruebas concluidas y descubrimientos por estado.

## Modelo de lenguaje: opcional y local

El motor (cuentas, auditoría, estadística) **no usa ningún modelo**. El modelo solo escribe la explicación para el gerente. Proveedores: `nenhum` (predeterminado), `ollama` (local), `claude-cli` (`claude -p` con tu suscripción) y `codex-cli` (`codex exec` con tu suscripción). Ninguno lee claves de API, y el texto enviado lleva solo números agregados — ningún nombre de cliente sale de la máquina.

## Arquitectura y próximos pasos

Hoy: Python puro + SQLite + HTML. Camino previsto en el documento de visión (detalles en [docs/ARQUITETURA.md](docs/ARQUITETURA.md)):

- **Supabase**: `schema.sql` ya trae las tablas para guardar el historial en Postgres.
- **n8n**: el flujo de ejemplo en `n8n/` ejecuta el ciclo cada semana y avisa a quien debe aprobar.
- **Next.js**: panel web multiusuario sobre el mismo `descobertas.json`.
- **Fase 2**: costos, márgenes y operaciones con conectores directos.
- **Fase 3**: aprendizaje entre empresas, solo con datos agregados y anonimizados, base legal, contrato y cumplimiento de la ley de protección de datos (LGPD en Brasil).

## Pruebas

```bash
python3 -m pytest -q   # 22 pruebas: cuentas del documento, auditoría, puerta humana, evaluación a ciegas, validación
```

## Licencia

MIT. Datos de ejemplo totalmente ficticios.
