export interface VerifiedActuatorEvidence {
  actuatorId: string;
  interlockHealthy: true;
  observedCommandHash: string;
}

export class ActuatorEvidence {
  public static acceptObservation(actuatorId: string, interlockHealthy: boolean, observedCommandHash: string): VerifiedActuatorEvidence {
    if (!actuatorId || !interlockHealthy || !/^[a-f0-9]{64}$/i.test(observedCommandHash)) {
      throw new Error("ACTION_REQUIRED: actuator/interlock evidence incomplete");
    }
    return { actuatorId, interlockHealthy: true, observedCommandHash: observedCommandHash.toLowerCase() };
  }
}
