import { apiClient } from "./client";

export interface IceServer {
  urls: string[];
  username?: string;
  credential?: string;
}

export async function getIceServers(): Promise<IceServer[]> {
  const resp = await apiClient.get<{ ice_servers: IceServer[] }>("/calls/ice-servers");
  return resp.data.ice_servers;
}
