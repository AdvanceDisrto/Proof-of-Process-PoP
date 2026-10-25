declare module "node:crypto" {
  interface Hash {
    update(data: string): Hash;
    digest(encoding: "hex"): string;
  }
  export function createHash(algorithm: string): Hash;
}

  export type KeyObject = object;
  export function verify(
    algorithm: string | null,
    data: Uint8Array,
    key: KeyObject,
    signature: Uint8Array,
  ): boolean;
