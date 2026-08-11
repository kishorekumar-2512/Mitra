"""Database adapter protocol and SQLAlchemy implementation."""
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Protocol
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from app.db.models import Base, Category, Product, Customer, Order, OrderItem, Review, Sale, Employee
import random

class DatabaseAdapter(Protocol):
    async def get_schema(self) -> dict[str, Any]: ...
    async def fetch_all(self, sql: str) -> tuple[list[str], list[dict[str, Any]]]: ...

class SQLAlchemyAdapter:
    def __init__(self, url: str) -> None:
        parsed = make_url(url)
        if parsed.drivername.startswith("sqlite") and parsed.database and parsed.database != ":memory:":
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        self.engine: AsyncEngine = create_async_engine(url)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def initialize_sample_data(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as session:
            if await session.get(Category, 1):
                return
            
            categories = [
                Category(id=1, name="Electronics", description="Gadgets and devices"),
                Category(id=2, name="Clothing", description="Apparel and fashion"),
                Category(id=3, name="Home & Kitchen", description="Home appliances and cookware"),
                Category(id=4, name="Books", description="Physical and digital books"),
                Category(id=5, name="Sports", description="Sporting goods and equipment"),
                Category(id=6, name="Toys", description="Toys and games for kids"),
                Category(id=7, name="Beauty", description="Cosmetics and personal care"),
                Category(id=8, name="Automotive", description="Car accessories and parts"),
            ]
            session.add_all(categories)

            products = []
            pid = 1
            for cat_id in range(1, 9):
                for i in range(1, 6):
                    cost = random.uniform(2.0, 200.0)
                    price = cost * random.uniform(1.2, 3.0)
                    products.append(Product(
                        id=pid,
                        name=f"Product {pid} - {categories[cat_id-1].name}",
                        category_id=cat_id,
                        cost=round(cost, 2),
                        unit_price=round(price, 2),
                        stock_quantity=random.randint(10, 500),
                        rating=round(random.uniform(2.5, 5.0), 1)
                    ))
                    pid += 1
            session.add_all(products)
            
            customers = []
            tiers = ["Bronze", "Silver", "Gold"]
            cities = ["New York", "London", "Tokyo", "Paris", "Sydney"]
            for i in range(1, 31):
                customers.append(Customer(
                    id=i,
                    name=f"Customer {i}",
                    email=f"customer{i}@example.com",
                    city=random.choice(cities),
                    country="Global",
                    join_date=date(2023, random.randint(1, 12), random.randint(1, 28)),
                    tier=random.choice(tiers)
                ))
            session.add_all(customers)

            orders = []
            statuses = ["completed", "pending", "shipped", "cancelled"]
            payments = ["Credit Card", "PayPal", "Bank Transfer"]
            for i in range(1, 81):
                orders.append(Order(
                    id=i,
                    customer_id=random.randint(1, 30),
                    order_date=date(2024, random.randint(1, 12), random.randint(1, 28)),
                    status=random.choice(statuses),
                    total_amount=0.0, # Will update
                    payment_method=random.choice(payments)
                ))
            session.add_all(orders)
            
            order_items = []
            item_id = 1
            for order in orders:
                total = 0.0
                num_items = random.randint(1, 3)
                for _ in range(num_items):
                    prod = random.choice(products)
                    qty = random.randint(1, 5)
                    discount = random.choice([0.0, 0.05, 0.1])
                    price = prod.unit_price
                    total += price * qty * (1 - discount)
                    order_items.append(OrderItem(
                        id=item_id,
                        order_id=order.id,
                        product_id=prod.id,
                        quantity=qty,
                        unit_price=price,
                        discount=discount
                    ))
                    item_id += 1
                order.total_amount = round(total, 2)
            session.add_all(order_items)

            sales = []
            sale_id = 1
            for _ in range(100):
                prod = random.choice(products)
                qty = random.randint(5, 50)
                sales.append(Sale(
                    id=sale_id,
                    product_id=prod.id,
                    sale_date=date(2025, random.randint(1, 6), random.randint(1, 28)),
                    quantity=qty,
                    revenue=round(qty * prod.unit_price, 2)
                ))
                sale_id += 1
            session.add_all(sales)
            
            reviews = []
            for i in range(1, 61):
                reviews.append(Review(
                    id=i,
                    product_id=random.randint(1, 40),
                    customer_id=random.randint(1, 30),
                    rating=random.randint(1, 5),
                    comment=f"Review comment {i}",
                    review_date=date(2024, random.randint(1, 12), random.randint(1, 28))
                ))
            session.add_all(reviews)
            
            employees = []
            depts = ["Sales", "Engineering", "HR", "Marketing", "Finance"]
            
            # CEO
            employees.append(Employee(id=1, name="Alice CEO", department="Management", salary=180000, hire_date=date(2020, 1, 1), manager_id=None))
            
            # Managers
            for i in range(2, 7):
                employees.append(Employee(id=i, name=f"Manager {i}", department=depts[i-2], salary=120000, hire_date=date(2021, 1, 1), manager_id=1))
                
            # Regular
            for i in range(7, 16):
                dept_idx = (i-7) % 5
                employees.append(Employee(id=i, name=f"Employee {i}", department=depts[dept_idx], salary=random.randint(45000, 90000), hire_date=date(2022, 1, 1), manager_id=dept_idx+2))
                
            session.add_all(employees)
            await session.commit()

    async def get_schema(self) -> dict[str, Any]:
        def reflect(sync_conn: Any) -> dict[str, Any]:
            inspector = inspect(sync_conn)
            tables = []
            for table in inspector.get_table_names():
                columns = [{"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"], "primary_key": c["primary_key"]} for c in inspector.get_columns(table)]
                fks = [{"column": fk["constrained_columns"][0], "references_table": fk["referred_table"], "references_column": fk["referred_columns"][0]} for fk in inspector.get_foreign_keys(table)]
                tables.append({"name": table, "columns": columns, "foreign_keys": fks})
            return {"tables": tables}
        async with self.engine.connect() as conn:
            return await conn.run_sync(reflect)

    async def fetch_all(self, sql: str) -> tuple[list[str], list[dict[str, Any]]]:
        async with self.engine.connect() as conn:
            result = await conn.execute(text(sql))
            columns = list(result.keys())
            rows = [{key: self._json_safe(value) for key, value in row._mapping.items()} for row in result.fetchall()]
            return columns, rows

    @staticmethod
    def _json_safe(value: Any) -> Any:
        return value.isoformat() if isinstance(value, (date,)) else value
