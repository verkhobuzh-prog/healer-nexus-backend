## Adding New Projects (e.g., eco-pulse)

### Phase 1 (Placeholder):

```python

# 1. Register as child project

registry.register_child_project("eco_pulse")

# 2. Create module stub

class EcoPulseModule(BaseModule):

    async def health_check(self):

        return {"module": "eco_pulse", "status": "healthy"}

# 3. Register module

registry.register(EcoPulseModule())

```

### Phase 2 (Real Implementation):

- Separate bot with own token (ECO_BOT_TOKEN)

- Own bot logic (app/telegram/eco_[bot.py](http://bot.py))

- Integration via event_bus

- Database queries filter by project_id="eco_pulse"

### Never Suggest:

❌ Creating separate repository for eco-pulse

❌ Splitting database into eco_pulse.db

❌ Microservices architecture without approval## ?? Adding New Projects (e.g., eco-pulse)
### Phase 1 (Placeholder):
1. Register as child project in registry.
2. Create module stub.
3. Register module.
### Phase 2 (Real Implementation):
- Separate bot with own token (ECO_BOT_TOKEN).
- Own bot logic (app/telegram/eco_bot.py).
- Integration via event_bus.
- Database queries filter by project_id='eco_pulse'.
### ? Never Suggest:
- Creating separate repository for eco-pulse.
- Splitting database into eco_pulse.db.
- Microservices architecture without approval.
