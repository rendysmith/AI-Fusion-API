"""Full refactor to SaaS billing models

Revision ID: 0268b3d42e61
Revises: 
Create Date: 2025-11-10 13:33:25.421432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0268b3d42e61'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Шаг 1: Создаем все НОВЫЕ таблицы (Код Alembic здесь ПРАВИЛЬНЫЙ) ---
    op.create_table('ai_models',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('provider', sa.String(length=50), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('is_available', sa.Boolean(), nullable=False),
    sa.Column('is_new', sa.Boolean(), nullable=False),
    sa.Column('is_best', sa.Boolean(), nullable=False),
    sa.Column('icon_url', sa.String(length=255), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=True),
    sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_models_category'), 'ai_models', ['category'], unique=False)
    op.create_index(op.f('ix_ai_models_slug'), 'ai_models', ['slug'], unique=True)

    op.create_table('subscription_plans',
    # ... (весь твой 'create_table' для subscription_plans - он правильный) ...
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('price', sa.Integer(), nullable=False),
    sa.Column('daily_generation_limit', sa.Integer(), nullable=False),
    sa.Column('concurrent_generation_limit', sa.Integer(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_subscription_plans_slug'), 'subscription_plans', ['slug'], unique=True)

    op.create_table('plan_model_access',
    # ... (весь твой 'create_table' для plan_model_access - он правильный) ...
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=False),
    sa.Column('model_id', sa.Integer(), nullable=False),
    sa.Column('generation_limit', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['model_id'], ['ai_models.id'], ),
    sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('plan_id', 'model_id', name='uq_plan_model_access')
    )

    op.create_table('user_subscriptions',
    # ... (весь твой 'create_table' для user_subscriptions - он правильный) ...
    sa.Column('id', sa.String(length=100), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('is_manual', sa.Boolean(), nullable=True),
    sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('get_course_deal_id', sa.String(length=100), nullable=True),
    sa.Column('get_course_deal_number', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_user_subscriptions_get_course_deal_number'), 'user_subscriptions', ['get_course_deal_number'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_plan_id'), 'user_subscriptions', ['plan_id'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_status'), 'user_subscriptions', ['status'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_user_id'), 'user_subscriptions', ['user_id'], unique=False)

    op.create_table('payment_invoices',
    # ... (весь твой 'create_table' для payment_invoices - он правильный) ...
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('subscription_id', sa.String(length=100), nullable=False),
    sa.Column('amount', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=10), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('failure_reason', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['subscription_id'], ['user_subscriptions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_invoices_subscription_id'), 'payment_invoices', ['subscription_id'], unique=False)

    # --- Удаляем 'prompts' (Alembic сгенерил, это ок) ---
    op.drop_table('prompts')

    # --- Шаг 2: РУЧНОЙ ФИКС для completed_task_log ---
    # Мы переименовываем, а не удаляем/добавляем
    op.alter_column('completed_task_log',
        'model_name',
        new_column_name='model_slug',
        existing_type=sa.String(length=100),
        existing_nullable=False,
        existing_server_default=False
    )
    op.drop_index(op.f('ix_completed_task_log_model_name'), table_name='completed_task_log')
    op.create_index(op.f('ix_completed_task_log_model_slug'), 'completed_task_log', ['model_slug'], unique=False)

    # --- Шаг 3: РУЧНОЙ ФИКС для generation_tasks ---
    # Переименовываем 'model_name' -> 'model_slug'
    op.alter_column('generation_tasks',
        'model_name',
        new_column_name='model_slug',
        existing_type=sa.String(length=100),
        existing_nullable=False
    )
    # Добавляем новые колонки/индексы (это Alembic сгенерил, это ок)
    op.add_column('generation_tasks', sa.Column('provider_job_id', sa.String(length=100), nullable=True))
    op.drop_index(op.f('ix_generation_tasks_model_name'), table_name='generation_tasks')
    op.create_index(op.f('ix_generation_tasks_model_slug'), 'generation_tasks', ['model_slug'], unique=False)
    op.create_index(op.f('ix_generation_tasks_provider_job_id'), 'generation_tasks', ['provider_job_id'], unique=False)
    # Привязываем ForeignKey к НОВОЙ таблице
    ai_models_table = sa.table(
        'ai_models',
        sa.Column('name', sa.String),
        sa.Column('slug', sa.String),
        sa.Column('description', sa.Text),
        sa.Column('provider', sa.String),
        sa.Column('category', sa.String),
        sa.Column('is_available', sa.Boolean),
        sa.Column('is_new', sa.Boolean),
        sa.Column('is_best', sa.Boolean),
        sa.Column('sort_order', sa.Integer),
        sa.Column('settings', postgresql.JSONB)
    )

    # Вставь сюда ВСЕ модели, которые у тебя есть в коде (schemas.py)
    # и которые могут быть в 'generation_tasks'
    op.bulk_insert(ai_models_table,
                   [
                       {
                           'name': 'Sora 2', 'slug': 'sora-2', 'description': 'Default Sora Model',
                           'provider': 'Kie AI', 'category': 'video', 'is_available': True,
                           'is_new': False, 'is_best': True, 'sort_order': 1,
                           # --- ИСПРАВЛЕНО: Просто строка, а не sa.text() ---
                           'settings': '{"cost": 0.1, "prime_cost": 0.05}'
                       },
                       {
                           'name': 'Veo 3 Quality', 'slug': 'veo-3-quality', 'description': 'Default Veo Quality',
                           'provider': 'Kie AI', 'category': 'video', 'is_available': True,
                           'is_new': True, 'is_best': False, 'sort_order': 2,
                           # --- ИСПРАВЛЕНО: Просто строка, а не sa.text() ---
                           'settings': '{"cost": 0.2, "prime_cost": 0.1}'
                       },
                       {
                           'name': 'Veo 3 Fast', 'slug': 'veo-3-fast', 'description': 'Default Veo Fast',
                           'provider': 'Kie AI', 'category': 'video', 'is_available': True,
                           'is_new': True, 'is_best': False, 'sort_order': 3,
                           # --- ИСПРАВЛЕНО: Просто строка, а не sa.text() ---
                           'settings': '{"cost": 0.05, "prime_cost": 0.02}'
                       }
                   ]
                   )

    # --- Шаг 4: РУЧНОЙ ФИКС для user_model_stats ---
    op.drop_constraint('uq_user_model_stats', 'user_model_stats', type_='unique')
    op.alter_column('user_model_stats',
        'model_name',
        new_column_name='model_slug',
        existing_type=sa.String(length=100),
        existing_nullable=False
    )
    op.create_unique_constraint('uq_user_model_stats', 'user_model_stats', ['user_id', 'model_slug'])

    # --- Шаг 5: Обновляем 'users' (Alembic сгенерил, это ок) ---
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('users', sa.Column('is_blocked', sa.Boolean(), server_default='false', nullable=True))
    # Делаем NOT NULL (в 2 шага, чтобы не было 'NotNullViolation')
    op.execute('UPDATE users SET is_admin = false WHERE is_admin IS NULL')
    op.execute('UPDATE users SET is_blocked = false WHERE is_blocked IS NULL')
    op.alter_column('users', 'is_admin', nullable=False)
    op.alter_column('users', 'is_blocked', nullable=False)

    # --- Шаг 6: Удаляем 'prices' (Alembic сгенерил, это ок) ---
    op.drop_table('prices')

    op.create_foreign_key('fk_generation_tasks_model_slug_ai_models', 'generation_tasks', 'ai_models', ['model_slug'], ['slug'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###

    # --- Восстанавливаем 'prices' ---
    op.create_table('prices',
        sa.Column('model_name', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
        sa.Column('cost', sa.DECIMAL(precision=15, scale=6), autoincrement=False, nullable=False),
        sa.Column('prime_cost', sa.DECIMAL(precision=15, scale=6), autoincrement=False, nullable=False),
        sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('model_name', name='prices_pkey')
    )
    op.create_index('ix_prices_model_name', 'prices', ['model_name'], unique=False)

    # --- Откатываем 'users' ---
    op.drop_column('users', 'is_blocked')
    op.drop_column('users', 'is_admin')

    # --- Откатываем 'user_model_stats' (РУЧНОЙ ФИКС) ---
    op.drop_constraint('uq_user_model_stats', 'user_model_stats', type_='unique')
    op.alter_column('user_model_stats', 'model_slug', new_column_name='model_name', existing_type=sa.String(100))
    op.create_unique_constraint('uq_user_model_stats', 'user_model_stats', ['user_id', 'model_name'])

    # --- Откатываем 'generation_tasks' (РУЧНОЙ ФИКС) ---
    op.drop_constraint('fk_generation_tasks_model_slug_ai_models', 'generation_tasks', type_='foreignkey')
    op.drop_index(op.f('ix_generation_tasks_provider_job_id'), table_name='generation_tasks')
    op.drop_index(op.f('ix_generation_tasks_model_slug'), table_name='generation_tasks')
    op.create_index(op.f('ix_generation_tasks_model_name'), 'generation_tasks', ['model_name'], unique=False)
    op.drop_column('generation_tasks', 'provider_job_id')
    op.alter_column('generation_tasks', 'model_slug', new_column_name='model_name', existing_type=sa.String(100))

    # --- Откатываем 'completed_task_log' (РУЧНОЙ ФИКС) ---
    op.drop_index(op.f('ix_completed_task_log_model_slug'), table_name='completed_task_log')
    op.create_index(op.f('ix_completed_task_log_model_name'), 'completed_task_log', ['model_name'], unique=False)
    op.alter_column('completed_task_log', 'model_slug', new_column_name='model_name', existing_type=sa.String(100))

    # --- Восстанавливаем 'prompts' ---
    op.create_table('prompts',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('prompt', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='prompts_pkey')
    )

    # --- Удаляем НОВЫЕ таблицы ---
    op.drop_index(op.f('ix_payment_invoices_subscription_id'), table_name='payment_invoices')
    op.drop_table('payment_invoices')
    op.drop_index(op.f('ix_user_subscriptions_user_id'), table_name='user_subscriptions')
    op.drop_index(op.f('ix_user_subscriptions_status'), table_name='user_subscriptions')
    op.drop_index(op.f('ix_user_subscriptions_plan_id'), table_name='user_subscriptions')
    op.drop_index(op.f('ix_user_subscriptions_get_course_deal_number'), table_name='user_subscriptions')
    op.drop_table('user_subscriptions')
    op.drop_table('plan_model_access')
    op.drop_index(op.f('ix_subscription_plans_slug'), table_name='subscription_plans')
    op.drop_table('subscription_plans')
    op.drop_index(op.f('ix_ai_models_slug'), table_name='ai_models')
    op.drop_index(op.f('ix_ai_models_category'), table_name='ai_models')
    op.drop_table('ai_models')
    # ### end Alembic commands ###