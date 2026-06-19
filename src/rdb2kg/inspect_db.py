from dataclasses import dataclass, field
import sqlalchemy as sa


@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    primary_key: bool


@dataclass
class ForeignKeyInfo:
    constrained_columns: list[str]
    referred_table: str
    referred_columns: list[str]


@dataclass
class TableInfo:
    name: str
    row_count: int
    columns: list[ColumnInfo]
    foreign_keys: list[ForeignKeyInfo]


@dataclass
class DatabaseSchema:
    url: str
    tables: list[TableInfo]


def inspect_database(db_url: str) -> DatabaseSchema:
    engine = sa.create_engine(db_url)
    inspector = sa.inspect(engine)
    tables = []

    with engine.connect() as conn:
        for table_name in inspector.get_table_names():
            col_info = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = set(pk_constraint.get("constrained_columns", []))

            columns = [
                ColumnInfo(
                    name=col["name"],
                    type=str(col["type"]),
                    nullable=col.get("nullable", True),
                    primary_key=col["name"] in pk_cols,
                )
                for col in col_info
            ]

            fk_info = inspector.get_foreign_keys(table_name)
            foreign_keys = [
                ForeignKeyInfo(
                    constrained_columns=fk["constrained_columns"],
                    referred_table=fk["referred_table"],
                    referred_columns=fk["referred_columns"],
                )
                for fk in fk_info
            ]

            result = conn.execute(sa.text(f'SELECT COUNT(*) FROM "{table_name}"'))
            row_count = result.scalar()

            tables.append(TableInfo(
                name=table_name,
                row_count=row_count,
                columns=columns,
                foreign_keys=foreign_keys,
            ))

    engine.dispose()
    return DatabaseSchema(url=db_url, tables=tables)


def schema_to_yaml(schema: DatabaseSchema) -> str:
    lines = [f"database: {schema.url}", "tables:"]
    for table in schema.tables:
        lines.append(f"  {table.name}:")
        lines.append(f"    rows: {table.row_count}")

        pk_cols = [c.name for c in table.columns if c.primary_key]
        if pk_cols:
            lines.append(f"    primary_key: [{', '.join(pk_cols)}]")

        lines.append("    columns:")
        for col in table.columns:
            lines.append(f"      {col.name}: {col.type}")

        if table.foreign_keys:
            lines.append("    foreign_keys:")
            for fk in table.foreign_keys:
                child = ", ".join(fk.constrained_columns)
                parent = ".".join([fk.referred_table, fk.referred_columns[0]])
                if len(fk.constrained_columns) == 1:
                    lines.append(f"      - {{columns: [{child}], references: {parent}}}")
                else:
                    parent_cols = ", ".join(fk.referred_columns)
                    lines.append(
                        f"      - {{columns: [{child}], "
                        f"references: {fk.referred_table}.[{parent_cols}]}}"
                    )

    return "\n".join(lines)
