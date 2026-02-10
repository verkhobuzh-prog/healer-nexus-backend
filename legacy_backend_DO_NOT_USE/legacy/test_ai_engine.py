import asyncio
import sys
import os
sys.path.append(os.getcwd())
async def test():
    print('Try connect...')
    try:
        from app.ai.providers import engine
        res = await engine.analyze_data('Hello', 'Test')
        print(f'Result: {res}')
    except Exception as e:
        print(f'Error: {e}')
if __name__ == '__main__':
    asyncio.run(test())