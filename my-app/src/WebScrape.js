import React, { useState } from "react";
import axios from "axios";
import DownloadExcel from "./DownloadExcel";

import {
  Container,
  Typography,
  TextField,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
} from "@mui/material";

export default function WebScrape() {
  const [url, setUrl] = useState("");
  const [pages, setPages] = useState(1);
  const [fields, setFields] = useState("");
  const [listings, setListings] = useState([]);
  const [timestamp, setTimestamp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleScrape = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = {
        url,
        pages,
        fields: fields
          ? fields.split(",").map((f) => f.trim())
          : [],
      };
      const res = await axios.post('/api/scrape', payload)
      ;
      setListings(res.data.data.listings);
      setTimestamp(res.data.timestamp);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderTable = (rows) => {
    if (!rows.length) return <Typography>No listings found.</Typography>;
    const headers = Object.keys(rows[0]);
    return (
      <TableContainer component={Paper} sx={{ maxHeight: 400, mt: 2 }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              {headers.map((h) => (
                <TableCell
                  key={h}
                  sx={{ backgroundColor: "#7E57C2", fontWeight: "bold" }}
                >
                  {h.toUpperCase()}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((item, i) => (
              <TableRow key={i} hover>
                {headers.map((h) => (
                  <TableCell key={h}>
                    {Array.isArray(item[h])
                      ? item[h].join(", ")
                      : h.toLowerCase() === "link"
                      ? (
                        <a
                          href={item[h]}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {item[h]}
                        </a>
                      )
                      : item[h]}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Funda & Bestemmingsplan Dashboard
      </Typography>

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <TextField
          label="URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          fullWidth
          size="small"
        />
        <TextField
          label="Pages"
          type="number"
          value={pages}
          onChange={(e) => setPages(+e.target.value)}
          size="small"
          sx={{ width: 100 }}
        />
        <TextField
          label="Fields (comma separated)"
          value={fields}
          onChange={(e) => setFields(e.target.value)}
          fullWidth
          size="small"
        />
        <Button
          variant="contained"
          onClick={handleScrape}
          disabled={loading}
          sx={{ whiteSpace: "nowrap", px: 4 }}
        >
          {loading ? <CircularProgress size={24} /> : "Scrape & Export"}
        </Button>
      </div>

      {error && <Alert severity="error">{error}</Alert>}

      {listings.length > 0 && (
        <>
          <Typography variant="h6" sx={{ mt: 3 }}>
            Results
          </Typography>
          {renderTable(listings)}
          <DownloadExcel timestamp={timestamp} />
        </>
      )}
    </Container>
  );
}
