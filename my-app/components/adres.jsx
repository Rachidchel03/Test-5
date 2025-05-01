// src/components/AdresBestemming.jsx
import React, { useEffect, useState } from "react";
import { fetchBestemming } from "../api";  // zorg dat dit naar jouw api.js wijst
import { CircularProgress, List, ListItem, ListItemText, Typography } from '@mui/material';

export default function AdresBestemming({ addresses }) {
  const [results, setResults] = useState([]);    // [{ address, bestemming: [...] }]
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchAll() {
      setLoading(true);
      try {
        const all = await Promise.all(
          addresses.map(async addr => {
            const { bestemming } = await fetchBestemming(addr);
            return { address: addr, bestemming };
          })
        );
        setResults(all);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchAll();
  }, [addresses]);

  if (loading) return <CircularProgress />;
  if (error)  return <Typography color="error">Fout: {error}</Typography>;

  return (
    <div>
      <Typography variant="h6" gutterBottom>
        Bestemmingsplannen per adres
      </Typography>
      <List>
        {results.map(({ address, bestemming }, i) => (
          <ListItem key={i} alignItems="flex-start">
            <ListItemText
              primary={address}
              secondary={bestemming.length > 0 
                ? bestemming.join(", ") 
                : "Geen plan gevonden"}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
}
