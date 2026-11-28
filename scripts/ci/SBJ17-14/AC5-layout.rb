# AC5 helper: prints each user table's name, column families (with the attributes both HBase 1.4 and 2.6
# know) and region start keys, one "LAYOUT ..." line each, sorted, so two HBase versions can be compared.
# Uses only client calls present in both 1.4 and 2.6 (Admin#getTableDescriptor, RegionLocator#getStartKeys).
# Run: docker exec -i <hbase container> hbase shell -n < scripts/ci/SBJ17-14/AC5-layout.rb
include Java
conf = org.apache.hadoop.hbase.HBaseConfiguration.create
conn = org.apache.hadoop.hbase.client.ConnectionFactory.createConnection(conf)
admin = conn.getAdmin
admin.listTableNames.map { |t| t.getNameAsString }.sort.each do |name|
  tn = org.apache.hadoop.hbase.TableName.valueOf(name)
  puts "LAYOUT table #{name}"
  families = admin.getTableDescriptor(tn).getColumnFamilies.to_a.sort_by { |f| f.getNameAsString }
  families.each do |f|
    puts "LAYOUT family #{name} #{f.getNameAsString} VERSIONS=#{f.getMaxVersions} MIN_VERSIONS=#{f.getMinVersions} " \
         "TTL=#{f.getTimeToLive} BLOOMFILTER=#{f.getBloomFilterType} COMPRESSION=#{f.getCompressionType} " \
         "DATA_BLOCK_ENCODING=#{f.getDataBlockEncoding} IN_MEMORY=#{f.isInMemory} " \
         "KEEP_DELETED_CELLS=#{f.getKeepDeletedCells} BLOCKCACHE=#{f.isBlockCacheEnabled} " \
         "BLOCKSIZE=#{f.getBlocksize} REPLICATION_SCOPE=#{f.getScope}"
  end
  keys = conn.getRegionLocator(tn).getStartKeys.to_a.map { |k| org.apache.hadoop.hbase.util.Bytes.toStringBinary(k) }
  keys.sort.each { |k| puts "LAYOUT split #{name} [#{k}]" }
end
conn.close
puts "LAYOUT end"
exit
