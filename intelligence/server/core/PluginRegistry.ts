export type Plugin={execute:(action:string,parameters:string[],context:unknown)=>Promise<{data:unknown}>};
const plugins=new Map<string,Plugin>();
export const TailwindAIPluginRegistry={register:(layer:string,p:Plugin)=>plugins.set(layer,p),get:(layer:string)=>plugins.get(layer)};
