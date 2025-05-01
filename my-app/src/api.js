// src/api.js

import axios from 'axios';

export async function fetchBestemming(address) {
  const resp = await axios.get("http://localhost:8000/api/bestemming", {
    params: { address }
  });
  return resp.data;  // { bestemming: [...] }
}
