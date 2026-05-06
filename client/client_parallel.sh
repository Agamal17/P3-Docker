for i in {1..20}; do
  python client/client.py put a hello &
done
wait