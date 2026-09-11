const quantity=document.querySelector('#quantity'), total=document.querySelector('#total'), error=document.querySelector('#error');
quantity.value=localStorage.getItem('quantity')||'1';
function renderCart(){
  const count=Number(quantity.value);
  if(!Number.isInteger(count)||count<1||count>20){error.textContent='Enter a quantity from 1 to 20';return;}
  error.textContent='';localStorage.setItem('quantity',String(count));
  total.textContent=(count*100).toFixed(2);
}
document.querySelector('#update').onclick=renderCart;
renderCart();
