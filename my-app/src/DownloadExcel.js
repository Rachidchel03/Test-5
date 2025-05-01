import React from "react";
import { Button } from "@mui/material";

export default function DownloadExcel({ timestamp }) {
  const download = () => {
    window.location.href = `http://localhost:8000/api/download-excel?timestamp=${timestamp}`;
  };

  return (
    <Button
      variant="outlined"
      sx={{ mt: 2 }}
      onClick={download}
      disabled={!timestamp}
    >
      Download Excel
    </Button>
  );
}
