export interface BiologicalArchiveReceipt {
  sourceHash: string;
  dnaSequence: string;
  sequenceLengthBases: number;
  physicalSynthesisPerformed: false;
  state: "ENCODING_ONLY" | "ACTION_REQUIRED";
}

const DNA = ["A", "C", "G", "T"] as const;

function hexToDna(hex: string): string {
  const alphabet = ["A", "C", "G", "T"];
  let dna = "";
  for (const pair of hex.match(/../g) ?? []) {
    const value = Number.parseInt(pair, 16);
    dna += alphabet[(value >> 6) & 3];
    dna += alphabet[(value >> 4) & 3];
    dna += alphabet[(value >> 2) & 3];
    dna += alphabet[value & 3];
  }
  return dna;
}

function isSha256(value: string): boolean {
  return /^sha256:[0-9a-f]{64}$/.test(value);
}

/**
 * Deterministic DNA encoding only. No claim of physical synthesis, storage,
 * sequencing, or blockchain inscription is made here.
 */
export class BiologicalArchiver {
  public static async encodeToDNA(genesisRootHash: string): Promise<BiologicalArchiveReceipt> {
    if (!isSha256(genesisRootHash)) {
      throw new Error("DNA_ARCHIVE_REJECTED: expected sha256:<64 hex chars>");
    }
    const dnaSequence = hexToDna(genesisRootHash.slice("sha256:".length));
    if (dnaSequence.split("").some((base) => !DNA.includes(base as (typeof DNA)[number]))) {
      throw new Error("DNA_ARCHIVE_REJECTED: invalid encoded base");
    }
    return {
      sourceHash: genesisRootHash,
      dnaSequence,
      sequenceLengthBases: dnaSequence.length,
      physicalSynthesisPerformed: false,
      state: "ENCODING_ONLY",
    };
  }
}
