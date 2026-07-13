# Architecture Decision Records

Architecture Decision Records, or ADRs, document important technical and architectural choices made for the Open DataOps Platform. Each ADR captures the context, the decision, the alternatives or tradeoffs, and the consequences of that choice.

The project uses ADRs so decisions stay visible over time. They help future contributors understand why the platform is shaped the way it is, especially when a choice involves tradeoffs between local development, production realism, cost, simplicity, and long-term extensibility.

Create a new ADR when a decision changes the architecture, toolchain, data modeling approach, operational boundary, or project conventions in a meaningful way. Small implementation details usually do not need ADRs unless they establish a pattern other work should follow.

| ADR | Title                                | Status   |
| --- | ------------------------------------ | -------- |
| 001 | Why PostgreSQL                       | Accepted |
| 002 | E-commerce Demo Domain               | Accepted |
| 003 | Use dbt Core                         | Accepted |
| 004 | Preserve Raw Data & Clean in Staging | Accepted |
| 005 | Dimensional Modeling                 | Accepted |
| 006 | Separate Orchestration from Platform Jobs | Accepted |

Future ADRs should be added to this table when they are created.
