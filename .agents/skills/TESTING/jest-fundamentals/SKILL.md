---
name: jest-fundamentals
description: Jest setup, configuration, test runner, assertions, lifecycle hooks, coverage. Activates when user mentions "Jest config", "setup Jest", "Jest configuration", "test coverage", "Jest hooks", "beforeEach", "afterEach", "describe blocks", or wants to configure Jest for JavaScript/TypeScript projects.
version: 1.0.0
---

# Jest Fundamentals

Master Jest configuration, test structure, assertions, and lifecycle hooks for JavaScript and TypeScript projects.

## Jest Configuration

Create `jest.config.js` or `jest.config.ts` at project root:

```javascript
// jest.config.js
module.exports = {
  preset: 'ts-jest',                    // Use ts-jest for TypeScript
  testEnvironment: 'node',              // 'node' for backend, 'jsdom' for frontend
  roots: ['<rootDir>/src'],
  testMatch: [
    '**/__tests__/**/*.ts',
    '**/?(*.)+(spec|test).ts'
  ],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/**/index.ts'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  setupFilesAfterEnv: ['<rootDir>/src/test/setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1'      // Path alias support
  },
  clearMocks: true,
  restoreMocks: true
};
```

### TypeScript Configuration

For TypeScript projects, ensure `tsconfig.json` includes:

```json
{
  "compilerOptions": {
    "types": ["jest", "node"],
    "esModuleInterop": true
  }
}
```

### Setup File

Create `src/test/setup.ts` for global test configuration:

```typescript
// src/test/setup.ts
import { jest } from '@jest/globals';

// Extend Jest matchers
expect.extend({
  toBeWithinRange(received, floor, ceiling) {
    const pass = received >= floor && received <= ceiling;
    return {
      message: () =>
        `expected ${received} ${pass ? 'not ' : ''}to be within range ${floor} - ${ceiling}`,
      pass
    };
  }
});

// Global timeout for async tests
jest.setTimeout(10000);

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks();
});
```

## Test Structure

### Basic Test Structure

```typescript
describe('ComponentName', () => {
  // Group related tests
  describe('methodName', () => {
    it('should do expected behavior when given valid input', () => {
      // Arrange
      const input = 'test';

      // Act
      const result = methodName(input);

      // Assert
      expect(result).toBe('expected');
    });

    it('should throw error when given invalid input', () => {
      expect(() => methodName(null)).toThrow('Invalid input');
    });
  });
});
```

### AAA Pattern (Arrange-Act-Assert)

Structure every test with clear phases:

```typescript
it('should calculate total with discount', () => {
  // Arrange - Set up test data and conditions
  const cart = new ShoppingCart();
  cart.addItem({ name: 'Widget', price: 100 });
  const discount = 0.1;

  // Act - Execute the behavior being tested
  const total = cart.calculateTotal(discount);

  // Assert - Verify the expected outcome
  expect(total).toBe(90);
});
```

## Lifecycle Hooks

```typescript
describe('Database operations', () => {
  let connection;
  let testData;

  // Runs once before all tests in this describe block
  beforeAll(async () => {
    connection = await createTestConnection();
  });

  // Runs before each test
  beforeEach(async () => {
    testData = await seedTestData(connection);
  });

  // Runs after each test
  afterEach(async () => {
    await clearTestData(connection);
    jest.clearAllMocks();
  });

  // Runs once after all tests
  afterAll(async () => {
    await connection.close();
  });

  it('should query data', async () => {
    const result = await connection.query('SELECT * FROM users');
    expect(result.length).toBeGreaterThan(0);
  });
});
```

## Common Assertions

### Value Assertions

```typescript
// Equality
expect(value).toBe(expected);           // Strict equality (===)
expect(value).toEqual(expected);        // Deep equality for objects/arrays
expect(value).toStrictEqual(expected);  // Deep equality + undefined checks

// Truthiness
expect(value).toBeTruthy();
expect(value).toBeFalsy();
expect(value).toBeNull();
expect(value).toBeUndefined();
expect(value).toBeDefined();

// Numbers
expect(value).toBeGreaterThan(3);
expect(value).toBeGreaterThanOrEqual(3);
expect(value).toBeLessThan(5);
expect(value).toBeCloseTo(0.3, 5);      // Floating point comparison

// Strings
expect(str).toMatch(/pattern/);
expect(str).toContain('substring');
expect(str).toHaveLength(5);

// Arrays
expect(array).toContain(item);
expect(array).toContainEqual({ id: 1 });
expect(array).toHaveLength(3);

// Objects
expect(obj).toHaveProperty('key');
expect(obj).toHaveProperty('nested.key', 'value');
expect(obj).toMatchObject({ partial: 'match' });
```

### Error Assertions

```typescript
// Sync errors
expect(() => throwingFunction()).toThrow();
expect(() => throwingFunction()).toThrow('specific message');
expect(() => throwingFunction()).toThrow(CustomError);

// Async errors
await expect(asyncFunction()).rejects.toThrow('error message');
await expect(asyncFunction()).rejects.toBeInstanceOf(CustomError);
```

### Mock Assertions

```typescript
const mockFn = jest.fn();

expect(mockFn).toHaveBeenCalled();
expect(mockFn).toHaveBeenCalledTimes(2);
expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2');
expect(mockFn).toHaveBeenLastCalledWith('lastArg');
expect(mockFn).toHaveBeenNthCalledWith(1, 'firstCallArg');
expect(mockFn).toHaveReturnedWith('value');
```

## Async Testing

### Promises

```typescript
// Resolves
it('should resolve with data', async () => {
  await expect(fetchData()).resolves.toEqual({ id: 1 });
});

// Rejects
it('should reject with error', async () => {
  await expect(fetchInvalidData()).rejects.toThrow('Not found');
});

// Async/await
it('should fetch user data', async () => {
  const user = await fetchUser(1);
  expect(user.name).toBe('John');
});
```

### Timers

```typescript
describe('Timer functions', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should call callback after delay', () => {
    const callback = jest.fn();

    setTimeout(callback, 1000);

    expect(callback).not.toHaveBeenCalled();

    jest.advanceTimersByTime(1000);

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should run all pending timers', () => {
    const callback = jest.fn();

    setTimeout(callback, 1000);
    setTimeout(callback, 2000);

    jest.runAllTimers();

    expect(callback).toHaveBeenCalledTimes(2);
  });
});
```

## Coverage Reports

### Running with Coverage

```bash
# Generate coverage report
npm test -- --coverage

# Watch mode with coverage
npm test -- --coverage --watchAll

# Coverage for specific files
npm test -- --coverage --collectCoverageFrom='src/utils/**/*.ts'
```

### Coverage Thresholds

Enforce minimum coverage in `jest.config.js`:

```javascript
coverageThreshold: {
  global: {
    branches: 80,
    functions: 80,
    lines: 80,
    statements: 80
  },
  './src/critical/': {
    branches: 100,
    functions: 100,
    lines: 100
  }
}
```

## Running Tests

```bash
# Run all tests
npm test

# Watch mode
npm test -- --watch

# Run specific file
npm test -- path/to/test.ts

# Run tests matching pattern
npm test -- --testNamePattern="should calculate"

# Run tests in specific directory
npm test -- --testPathPattern="src/utils"

# Verbose output
npm test -- --verbose

# Update snapshots
npm test -- --updateSnapshot
```

## Best Practices

1. **One assertion per test** - Keep tests focused on single behaviors
2. **Descriptive names** - Test names should explain the scenario and expected outcome
3. **Independent tests** - Each test should run in isolation
4. **Fast tests** - Mock slow operations (network, file I/O, timers)
5. **Clean up** - Use afterEach to reset state between tests
6. **Avoid implementation details** - Test behavior, not internal implementation
