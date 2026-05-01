export class Mutex {
  constructor() {
    this.current = Promise.resolve();
  }

  async runExclusive(fn) {
    const previous = this.current;
    let release;
    this.current = new Promise((resolve) => {
      release = resolve;
    });
    await previous;
    try {
      return await fn();
    } finally {
      release();
    }
  }
}
