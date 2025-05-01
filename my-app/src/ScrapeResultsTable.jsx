// src/ScrapeResultsTable.jsx
import React from 'react';

const ScrapeResultsTable = ({ listings }) => {
  if (!listings || listings.length === 0) {
    return <p>No data available.</p>;
  }

  // Get table headers from the keys of the first listing.
  const headers = Object.keys(listings[0]);

  return (
    <div style={{ overflowX: 'auto' }}>
      <table border="1" cellPadding="10" cellSpacing="0" style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead style={{ backgroundColor: '#f2f2f2' }}>
          <tr>
            {headers.map(header => (
              <th key={header} style={{ textAlign: 'left', padding: '8px' }}>
                {header.charAt(0).toUpperCase() + header.slice(1)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {listings.map((item, idx) => (
            <tr key={idx}>
              {headers.map(header => (
                <td key={header} style={{ padding: '8px' }}>
                  {header === 'link'
                    ? <a href={item[header]} target="_blank" rel="noreferrer">{item[header]}</a>
                    : item[header]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ScrapeResultsTable;
